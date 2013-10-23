from __future__ import absolute_import

import threading, argparse, gevent, signal, sys
from arachne.utils import strip_open, Queue, get_out_name, make_path, pwd, err_dir, out_dir
from collections import deque
from celery import group
from gevent.pool import Pool
from gevent import monkey
from os import path

## base object that is used to initialize input with arguments
## useful for keeping state for input for scripts that require it
class InObject( object ):
    def __init__(self, item, **kwargs):
        self.item = item
        for k,v in kwargs.iteritems():
            setattr(self, k, v)

    def __str__(self):
        return self.item

    def __repr__(self):
        return self.item

## all scripts have one chooser instance that is used to pass arguments
## and to select what platform to run the script with 
class Chooser( object ):
    def __init__(self, name, desc, has_input=True, has_match=False):
        self.name = name

        self.parser = argparse.ArgumentParser(desc)
        subs = self.parser.add_subparsers(dest='sub_name')

        self.thread_parser = subs.add_parser('thread', add_help=False,
            help='Run jobs using multithreading')
        self.celery_parser = subs.add_parser('celery', add_help=False,
            help='Run jobs using celery')
        self.gevent_parser = subs.add_parser('gevent', add_help=False,
            help='Run jobs using gevent pool')

        self.args = self.parser.parse_known_args()[0]

        if self.args.sub_name == 'celery':
            self.subparser = self.celery_parser
            self.init_obj = self.init_async
            self.cls = Hopper
        elif self.args.sub_name == 'thread':
            self.subparser = self.thread_parser
            self.init_obj = self.init_local
            self.cls = Runner
        elif self.args.sub_name == 'gevent':
            self.subparser = self.gevent_parser
            self.init_obj = self.init_local
            self.cls = Pooler

        self.subparser.add_argument('-p','--proxy_file',
            help='File to load proxies from, one per line, formatted as 1.2.3.4:8080')
        self.subparser.add_argument('-u','--ua_file',
            help='File to load user agents from, one per line')
        self.subparser.add_argument('-j','--job_name', 
            help='Appends name to output files')
        self.subparser.add_argument('-o','--out_file', 
            help='Name of output file.  Overrides JOB_NAME')

        if has_input:
            self.subparser.add_argument('-s','--start', type=int, default=1,
                help='Number for line of where to start loading input file')
            self.subparser.add_argument('-n','--number', type=int,
                help='Number of total jobs to do')
            self.subparser.add_argument('-i','--in_file', 
                help='Name of input file')

        if has_match:
            self.subparser.add_argument('-m','--match', 
                help='Only match links with match value.  Can specify multiple values with delimiter')
            self.subparser.add_argument('-l','--delimiter', default=',',
                help='String to separate different match values')
            self.args = self.subparser.parse_known_args()[0]
            self.args.match = self.args.match.split(self.args.delimiter) if self.args.match else []
            if not self.args.job_name:
                self.args.job_name = self.args.job_name or ''
                self.args.job_name += '-'.join(self.args.match)

    ## some scripts share initilization routines, this is used to avoid repetition
    def init_common(self, cls, obj):
        pass

    def start(self):
        self.obj = self.cls(self.name, self.subparser, self.args)
        ## the base class is passed as an argument for methods that refer to self
        self.init_obj(self.cls, self.obj)
        self.init_common(self.cls, self.obj)
        self.obj.run()

class Base( object ):
    def __init__(self):
        self.input = deque()
        ## check if var/out and var/err exist, if not makes them
        make_path(out_dir)
        make_path(err_dir)

    ## the three following methods are the three phases used to initialize
    ## input for each script. certain scripts will overwrite one or more of 
    ## these methods for its particular input
    def inn_base(self):
        if self.args.in_file:   
            return strip_open(self.args.in_file)
        else:
            print('No input file specified!')
            return []

    def inn_action(self, items):
        if not hasattr(self.args,'number'):
            return items
        if self.args.start:
            items = items[self.args.start-1:]
        if self.args.number:
            items = items[:self.args.number]
        return items

    def inn_target(self):
        items = self.inn_action(self.inn_base())
        self.input.extend(items)

    def init_args(self, args):
        self.args = self.parser.parse_args(sys.argv[2:])
        self.args.job_name = self.args.job_name or ''
        self.browser_args = {   
            'proxy_file':   self.args.proxy_file, 
            'ua_file'   :   self.args.ua_file   
        }
        self.base_args = [self.browser_args]
        self.base_kwargs = {}

        ## if certain args have been set already during preprocessing of args
        ## as in appending match values for scripts with has_match, replace
        ## what has been parsed with what has been done already
        if args:
            for k,v in vars(args).iteritems():
                setattr(self.args, k,v)

class LocalBase( Base ):
    def __init__(self, name):
        super(LocalBase, self).__init__()
        self.name = name
        self.in_object = {}
        self.to_input = []

        ## these events let auxiliary threads communicate with main running
        ## threads so the threads don't exit before the other threads have exited
        self.seeded = threading.Event()
        self.done = threading.Event()

        if not hasattr(self, 'phases'):
            self.phases = [self.run_base]

        self.status_done = 0
        self.status_good = 0
        self.status_todo = 0

    def run_base(self, my_item):
        try:
            out = self.core(my_item, *self.base_args, **self.base_kwargs)
        except Exception as e:
            return self.error_catch(self.name, my_item, e)  
        if type(out) == list:
            self.output.extend(out)
        else:
            if out:
                self.output.append(self.out_format(my_item, out))

    def run_core(self, my_item):
        self.run_base(my_item)
        self.status_done += 1
        self.status()

    def out_base(self, out_item):
        self.status_good += 1
        out_name = get_out_name(self.name, self.args.job_name, self.args.out_file)
        with open(path.join(out_dir, out_name), 'a+') as f:
            print >> f, out_item

    def err_base(self, err_item):
        err_name = get_out_name(self.name, self.args.job_name, self.args.out_file)
        with open(path.join(err_dir, err_name),'a+') as f:
            print >> f, err_item

    def log_base(self, log_item):
        print(log_item)

    ## certain scripts format their output in a specific way, just a placeholder here
    def out_format(self, item, out):
        return item

    def inn_core(self):
        self.inn_target()
        self.seeded.set()
        self.status_todo += len(self.input)

    ## this method overwrites the base inn_target, providing an object initialized
    ## with arguments the script specifies via the in_object dict
    def inn_target(self):
        items = self.inn_action(self.inn_base())
        if self.in_object:
            self.input.extend([InObject(x, **self.in_object) for x in items])
        else:
            self.input.extend(items)

    def error_catch(self, error, item, exception):
        msg = '{} | {} | {} -- {}'.format(self.name,error,item,exception)
        self.logger.append(msg)
        self.errors.append(msg)

    def status(self, suffix = '', prefix = ''):
        msg = 'Done: {}/{} || Good: {}'.format(self.status_done, self.status_todo, self.status_good)
        self.logger.append(prefix + msg + suffix)

## this is the base class for scripts to run on gevent, named after its main component, the gevent pool
class Pooler( LocalBase ):
    def __init__(self, name, subparser, args):
        super(Pooler, self).__init__(name)
        self.parser = argparse.ArgumentParser(parents=[subparser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        self.parser.add_argument('-c', '--concurrency', type=int, default=20,
            help='Size of gevent pool to run jobs with')

        self.init_args(args)

    ## the add methods here and in runner are used not only by the run method
    ## but also by the scripts themselves when they need to add items back into the input queue
    def add(self, item):
        self.status_todo += 1
        self.pool.spawn(self.run_core, item)

    def run(self):
        self.input = Queue()

        ## compared to the multithreaded code, only one thread is running with gevent
        ## so it is safe to have a callback that calls the respective auxiliary base
        self.logger = Queue(callback=self.log_base)
        self.errors = Queue(callback=self.err_base)
        self.output = Queue(callback=self.out_base)
        self.pool = Pool(self.args.concurrency)
        self.inn_core()

        gevent.monkey.patch_all(thread=False)
        if self.phases == [self.run_base]:
            self.run_target()
        else:
            for phase in self.phases:
                self.run_base = phase
                self.run_target()
                self.input.extend(self.to_input)
                self.to_input = []
        self.status(prefix='\nFinished! -- ')

    def run_target(self):
        while self.input or not self.seeded.is_set():
            my_item = self.input.popleft()
            self.pool.spawn(self.run_core, my_item)       
        self.pool.join()

## this is the base class for multithreaded code
class Runner( LocalBase ):
    def __init__(self, name, subparser, args):
        super(Runner, self).__init__(name)
        
        self.parser = argparse.ArgumentParser(parents=[subparser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
        self.parser.add_argument('-t','--threads', type=int, default=1,
            help='Number of threads to run jobs with')

        self.init_args(args)
        self.output = deque()
        self.errors = deque()
        self.logger = deque()

        self.name = name

        ## these are used to listen for ctrl+c interrupts and quit all threads
        self.interrupt = threading.Event()      
        signal.signal(signal.SIGINT, self.int_handler)

    def add(self, item):
        if self.interrupt.is_set():
            return
        self.status_todo += 1
        ## as opposed to the pooler code, each thread is continually checking to see if there
        ## is still input enqueued, so it is safe to append the input even if we have already
        ## gone through all of the initial input
        if len(self.threads) == self.args.threads:
            self.input.append(item)
        else:
            t = threading.Thread(target=self.run_base, args=(item,))
            self.threads.append(t)
            t.start()
            self.status_done += 1
            self.status()

    def start_threads(self):
        self.threads = []
        for i in xrange(self.args.threads):
            t = threading.Thread(target=self.run_target)
            self.threads.append(t)
            t.start()

        ## this is a bit of magic, but it works cross platform and it's great for testing out new 
        ## code without having to close a terminal/console since threads are hanging when code didn't
        ## exit gracefully -- not to mention terminating large batch jobs early
        while self.threads:
            try:
                temp = self.threads.pop()
                ## normally, calling join will interrupt the main thread, so any signals will not
                ## get registered until the thread succesfully joins.  if a thread is in an infinite loop,
                ## the signal will never get received. using a timeout allows the main thread to succesfully
                ## receive the intended signal, which will actually throw an exception (for some yet unknown reasons) 
                ## if we receive an exception it means that an interrupt was received, so we set the done lock
                ## so auxiliary threads can clean up and exit.  the isalive method of the thread checks to see if join
                ## was succesful, if it wasn't, we append it back to our list of running threads
                temp.join(timeout=0.1)
                if temp.isAlive():
                    self.threads.append(temp)
            except Exception as e:
                self.done.set()
                sys.exit(0)

    def run(self, *args, **kwargs):
        ## we need a seperate thread for anything that writes to a console or a file,
        ## since multiple threads will write on top of each other
        inn = threading.Thread(target=self.inn_core)
        out = threading.Thread(target=self.out_core)
        err = threading.Thread(target=self.err_core)
        log = threading.Thread(target=self.log_core)
        aux = [inn,out,err,log]
        for t in aux:
          t.start()

        if self.phases == [self.run_base]:
            self.start_threads()
        else:
            for phase in self.phases:
                self.run_base = phase           
                self.start_threads()
                self.input.extend(self.to_input)
                self.to_input = []
        self.done.set()
        for t in aux:
            t.join()

    def int_handler(self, signum, frame):
        print('Received interrupt signal!\nExiting..')
        self.interrupt.set()

    def main_loop(self, queue, lock,  base):
        while (queue or not lock.is_set()) and not self.interrupt.is_set():
            if queue:
                base(queue.popleft())

    def out_core(self):
        self.main_loop(self.output, self.done, self.out_base)
        self.status(prefix='\nFinished! -- ')
        print(self.logger.popleft())

    def log_core(self):
        self.main_loop(self.logger, self.done, self.log_base)

    def err_core(self):
        self.main_loop(self.errors, self.done, self.err_base)

    def run_target(self):
        self.main_loop(self.input, self.seeded, self.run_core)

## this is the base class for celery tasks, all it does is initialize arguments,
## load the input, and start a task for each work unit to be done
class Hopper( Base ):
    def __init__(self, name, subparser, args):
        super(Hopper, self).__init__()
        self.parser = argparse.ArgumentParser(parents=[subparser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        self.parser.add_argument('-q','--queue', default='celery',
            help='Specifies queue to feed tasks into')

        self.init_args(args)
        self.base_args += [
            self.args.job_name,
            self.args.out_file
        ]

    def run(self):
        self.inn_target()
        group(self.core.subtask( [item] + self.base_args, 
            self.base_kwargs).set(queue=self.args.queue) for item in self.input)()
        print('Loaded {} tasks.'.format(len(self.input)))
from __future__ import absolute_import
from collections import OrderedDict
from pybloom import BloomFilter
from os import path, makedirs
from celery import Task
from gevent.queue import Queue
from arachne.celery import celery
import errno, sys

## these directories are used to output results from scripts and errors, 
## we specify the directories on the root of the virtualenv
pwd = path.split(path.split(sys.argv[0])[0])[0]
out_dir = path.join(pwd, 'var', 'out')
err_dir = path.join(pwd, 'var', 'err')

def make_path(path):
    try:
        makedirs(path)
    except OSError as e:
        ## makedirs will throw an exception if the dir we're trying to make already exists
        ## if it is this particular exception, we ignore it
        if e.errno != errno.EEXIST:
            raise

## returns a dictionary with keys and values filled for parameters of a URL
def parse_params(p):
    params = OrderedDict()
    for keyval in p.split('&'):
        kv = keyval.split('=')
        key = kv[0]
        val = '' if len(kv) == 1 else kv[1]
        params[key] = val
    return params

## given a scheme+netloc and a dictionary of parameters as returned by parse_params
## returns a fully qualified url with parameters in GET request format
def gen_url(url, p):
    params = ''
    for key,val in p.items():
        params += '&{}={}'.format(key,val)
    ## the [1:] removes the leading &
    return '{}?{}'.format(url, params[1:])

## for each parameter, add to the value the change argument
## optionally we don't keep the initial value
def replace_params(url, change, keep_original=True):
    if url.count('?') != 1:
        return []
    link, param = url.split('?')
    params = parse_params(param)

    new_urls = []
    for key,val in params.iteritems():
        copy = OrderedDict(params)
        copy[key] = change
        if keep_original:
            copy[key] += val
        new_urls.append(gen_url(link, copy))
    return new_urls

def strip_open(in_file):
    with open(in_file, 'r+') as f:
        return [x.strip() for x in f.readlines()]

def get_out_name(name, job_name, out_name):
    if out_name:
        return out_name
    if job_name:
        return name + '-' + job_name
    return name

## this is mainly a placeholder, since in production we would be running celery
## on multiple machines, it does not make sense to write out to a file.  
## ideally we want to have a database connection and write to a table for each script
## however, since this is mainly proof of concept, there is no need to set up a database,
## though this structure allows for a rather easy implementation of that
@celery.task()
def celery_output(item, name, job_name, out_name):
    out_file = get_out_name(name, job_name, out_name)

    if type(item) == list:
        to_write = item
    else:
        to_write = [item]

    with open(path.join(out_dir, out_file), 'a+') as f:
        for item in to_write:
            print >> f, item
    return to_write

## this is just a subclass of the BloomFilter that adds an append method to be 
## interoperable with code that is used to lists instead of bloom filters.  the reason
## we use bloom filters instead of a list for celery code is that serializing and sending
## a list is a lot more expensive than a bf which when gzipped makes a big difference
class BloomFilter( BloomFilter ):
    def append(self, key):
        return self.add(key)

## the standard gevent queue subclassed to allow for callbacks on enqueueing and with
## support for boolean checking, length, and the extend method for lists
class Queue( Queue ):
    def __init__(self, callback=None):
        super(Queue, self).__init__()
        self.callback = callback

    def __nonzero__(self):
        return not self.empty()

    def __len__(self):
        return self.qsize()

    def check_callback(self, item):
        if self.callback:
            self.callback(item)

    def append(self, item):
        self.put(item)
        self.check_callback(item)

    def extend(self, items):
        for item in items:
            self.put(item)
            self.check_callback(item)

    def popleft(self):
        return self.get()
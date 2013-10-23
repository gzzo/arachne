arachne
=======
arachne is a small framework for creating scripts to scan, scrape, and play with the web on multiple runtimes.

Getting Started
---------------

arachne runs on Python 2.7. It is highly recommended you make a virtualenv for your arachne installation.  Since arachne uses lxml.html, you need to have the libxml2 and libxslt packages.  You will also need libevent to run gevent.  On windows, it is recommended to get the [lxml binary](http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml) and the [gevent binary](http://www.lfd.uci.edu/~gohlke/pythonlibs/#gevent).

```bash
:~/dev# sudo apt-get install libxml2-dev libxslt-dev libevent-dev
:~/dev# git clone https://github.com/gzzo/arachne
:~/dev# cd arachne
:~/dev/arachne# virtualenv-2.7 .
```

For old versions of virtualenv, there is an included script to set your PATH:
```bash
:~/dev/arachne# . setpath
```

Otherwise, it is recommended to use the included activate script:
```bash
:~/dev/arachne# . bin/activate
:~/dev/arachne# python setup.py install
```

Using arachne
-------------

arachne has three modes of running each script: through the multithreading module, through gevent pools, and by using the [celery framework](http://www.celeryproject.org/) through celery workers.  

> If you plan on using celery, you must configure your celeryconfig.py.  An example celeryconfig.py is provided.  

> To learn more about configuring celery, visit their [docs](http://docs.celeryproject.org/en/latest/configuration.html).

> In any case, you __must__ copy celeryconfig.py to your virtualenv bin/ or run scripts with it in your current directory.

```bash
:~/dev/arachne# cp arachne/celeryconfig.py bin/
:~/dev/arachne# mkdir lists
:~/dev/arachne# echo "http://python.org/" > lists/mylink
:~/dev/arachne# scrape_links gevent -i lists/mylink 
Done: 1/1 || Good: 94

Finished! -- Done: 1/1 || Good: 94
```

arachne will save the output of the scripts to the root of the virtualenv, under `var/out`.  By default, the name of the output file is the name of the script, to specify your own you can use the -j argument to append a job name to the name of the script, or the -o argument to specficy the name of the output file.

```bash
:~/dev/arachne/var/out# tail link-scraper
http://www.pycon.org/
http://python.org/download/releases/3.4.0/
http://python.org/download/releases/2.6.9/
http://www.pytennessee.org/
https://ironpython.codeplex.com/releases/view/90087
http://python.org/channews.rdf
http://python.org/about/website
http://www.xs4all.com/
http://www.timparkin.co.uk/
http://python.org/about/legal
```

Using Celery
-------
By default celery uses the multiprocessing module.  You can specify a different runtime for each worker using the -P argument.  For more information about celery workers, visit their [docs](http://docs.celeryproject.org/en/latest/userguide/workers.html).
```
:~/dev/arachne# celery worker -A arachne.celery -l INFO -E -P gevent
 -------------- celery@dowork v3.0.24 (Chiastic Slide)
---- **** ----- 
--- * ***  * -- Linux-3.7-trunk-amd64-x86_64-with-debian-1.0
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> broker:      amqp://fooman@192.168.1.105:5672/theshoe
- ** ---------- .> app:         arachne.celery:0x169cd50
- ** ---------- .> concurrency: 2 (gevent)
- *** --- * --- .> events:      ON
-- ******* ---- 
--- ***** ----- [queues]
 -------------- .> celery:      exchange:celery(direct) binding:celery
                

[Tasks]
  . arachne.scripts.check_keyword
  . arachne.scripts.check_proxy
  . arachne.scripts.check_rlfi
  . arachne.scripts.exploit_wp_brute.WpList
  . arachne.scripts.exploit_wp_leaguemanager
  . arachne.scripts.scan_dom
  . arachne.scripts.scan_rlfi
  . arachne.scripts.scan_sqli
  . arachne.scripts.scan_wp
  . arachne.scripts.scan_xss
  . arachne.scripts.scrape_alexa
  . arachne.scripts.scrape_headers
  . arachne.scripts.scrape_links
  . arachne.scripts.scrape_quantcast
  . arachne.scripts.scrape_proxy
  . arachne.scripts.smtp_send
  . arachne.scripts.sqli_dump
  . arachne.scripts.test_xss
  . arachne.scripts.wp_brute
  . arachne.scripts.wp_init
  . arachne.scripts.wp_user
  . arachne.utils.celery_output

[2013-10-21 21:00:35,114: WARNING/MainProcess] celery@dowork ready.
[2013-10-21 21:00:35,124: INFO/MainProcess] consumer: Connected to amqp://fooman@192.168.1.105:5672/theshoe.
[2013-10-21 21:00:35,154: INFO/MainProcess] pidbox: Connected to amqp://fooman@192.168.1.105:5672/theshoe.


```
Comparing Runtimes
---------------
One of the most useful things about being able to run scripts on multiple runtimes is the ability to compare how long a script takes to execute with the same input

```
:~/dev/arachne# time scrape_links gevent -i lists/mylink 
Done: 1/1 || Good: 94

Finished! -- Done: 1/1 || Good: 94

real    0m0.509s
user    0m0.180s
sys 0m0.040s
:~/dev/arachne# time scrape_links thread -i lists/mylink 
Done: 1/1 || Good: 0

Finished! -- Done: 1/1 || Good: 94

real  0m0.534s
user  0m0.552s
sys 0m0.164s
root@iPhone:~/dev/venv# time scrape_links celery -i lists/mylink
Loaded 1 tasks.

real    0m0.281s
user  0m0.216s
sys 0m0.040s

## and from the celery worker log
[2013-10-21 20:39:01,179: INFO/MainProcess] Got task from broker: arachne.scripts.scrape_links[4316f328-ffeb-44e8-ab2b-4ea327ebdab6]
[2013-10-21 20:39:01,181: INFO/MainProcess] Starting new HTTP connection (1): python.org
[2013-10-21 20:39:01,500: INFO/MainProcess] Task arachne.scripts.scrape_links[4316f328-ffeb-44e8-ab2b-4ea327ebdab6] succeeded in 0.321036100388s: None
[2013-10-21 20:39:01,503: INFO/MainProcess] Got task from broker: arachne.utils.celery_output[8c4dc664-f4d3-47f1-adaf-1b3227180bcf]
[2013-10-21 20:39:01,504: INFO/MainProcess] Task arachne.utils.celery_output[8c4dc664-f4d3-47f1-adaf-1b3227180bcf] succeeded in 0.000701904296875s: None
```
arachne Scripts
----------------

Each arachne script comes with a standard argparse help output.  Keep in mind to pass which runtime you want help for, since each runtime uses different parameters -- the celery runtime can specify which queue you want to send tasks to, while multithreading and gevent runtimes can specify how many threads/greenlets to spawn, respectively.

```
:~/dev/arachne# scrape_links -h
usage: Scrapes links from list of URLs [-h] {thread,celery,gevent} ...

positional arguments:
  {thread,celery,gevent}
    thread              Run jobs using multithreading
    celery              Run jobs using celery
    gevent              Run jobs using gevent pool

optional arguments:
  -h, --help            show this help message and exit
:~/dev/arachne# scrape_links thread -h
usage: scrape_links [-h] [-p PROXY_FILE] [-u UA_FILE] [-j JOB_NAME]
                    [-o OUT_FILE] [-s START] [-n NUMBER] [-i IN_FILE]
                    [-m MATCH] [-l DELIMITER] [-d DEPTH] [-e] [-t THREADS]

optional arguments:
  -h, --help            show this help message and exit
  -p PROXY_FILE, --proxy_file PROXY_FILE
                        File to load proxies from, one per line, formatted as
                        1.2.3.4:8080
  -u UA_FILE, --ua_file UA_FILE
                        File to load user agents from, one per line
  -j JOB_NAME, --job_name JOB_NAME
                        Appends name to output files
  -o OUT_FILE, --out_file OUT_FILE
                        Name of output file. Overrides JOB_NAME
  -s START, --start START
                        Number for line of where to start loading input file
  -n NUMBER, --number NUMBER
                        Number of total jobs to do
  -i IN_FILE, --in_file IN_FILE
                        Name of input file
  -m MATCH, --match MATCH
                        Only match links with match value. Can specify
                        multiple values with delimiter
  -l DELIMITER, --delimiter DELIMITER
                        String to separate different match values
  -d DEPTH, --depth DEPTH
                        Crawl links recursively up to DEPTH
  -e, --include_external
                        Include sites outside of netloc for scraping
  -t THREADS, --threads THREADS
                        Number of threads to run jobs with

```
___

script | description
------ | -----------
check_keyword | Visits a list of URLs and checks to see if they include any key from a list of keywords.  Can also specify to the URL for keywords, useful for checking against redirects.
check_proxy | Visits a specific site checking for a specific keyword with a list of proxies.
scrape_alexa | Downloads the top million sites ranked by Alexa.
scrape_quantcast | Downloads the top sites ranked by Quantcast, can specify which ranges with -r, in the hundreds.
scrape_links | Scrapes all the links from a website, optionally also recursively visit each link for additional links up to a specific depth.  Can also only get links that contain certain substrings, such as = or php.
scrape_headers | Gets the header information from a website, optionally specify which headers to retrieve.
scrape_proxy | Retrieves proxy list from hidemyass's free list, can also specify range of page numbers.
scan_rlfi | Checks each parameter of a URL for local and remote file inclusions.
scan_sqli | Does a very simple check to see any parameter in a URL is susceptible to SQL injection.
scan_xss | Checks for stored XSS in parameters and for DOM-based XSS in javascript files.
scan_wp | Traverses a couple of common directories of a domain to find a wp-login.php page.
exploit_wp_leaguemanager | Implementation of CVE-2013-1852
exploit_wp_brute | Performs a brute force attack against a wp-login.php page.  The password file provided with arachne contains [the 10,000 most popular](https://xato.net/passwords/more-top-worst-passwords/) passwords.  If you would rather use your own, name it wp_pass and place it in arachne/scripts/defaults/wp_pass, or just edit the script itself.
exploit_wp_sqli_dump | Given a URL with a SQLi vulnerability, a unique identifier to replace the id number in the query, and left and right ends of where to grab the output from, will query the site from a given start and end number range.
smtp_send | Sends emails through SMTP to a list of emails from a list of hostnames and logins.

Extending arachne
-----------------
For a good example of a simple arachne script, check the source of scripts/scrape_headers.  The basic imports are
```python
from arachne.base import Chooser
from arachne.utils import celery_output
from arachne.browser import Browser
from arachne.celery import celery
```

Which set up your main class, celery, and the engine behind most scripts, the browser.  After that the files will include one or more global methods, a celery task which usually will call the global method(s), and the main Chooser subclass which sets up additional arguments and tells arachne what to run for the script.  It also provides the name of the script for outputting and a general description for --help.

What actually defines your Chooser sublass are the init_ methods

```python
    #from arachne/scripts/scrape_headers.py
    def init_common(self, cls, obj):
        obj.base_args += [self.args.match]

    def init_async(self, cls, obj):
        obj.core = scrape_headers

    def init_local(self, cls, obj):
        cls.out_format = out_format
        obj.core = base_scrape_headers
```

Since the gevent and multithreading runtimes are so different from celery, there are two types of methods, one for the former group and one for the latter.  `init_common` is used for properties they share in common.  In this example, base_args is the list of arguments passed to the core running function.  `obj.core` defines these core running functions, and `cls.out_format` specifies how to format the output from the base method.  In the future, it might be possible to use a celery task's collect method and unify the two differing runtimes.


For a more involved example take a look at scripts/scrape_links and finally scripts/exploit_wp_brute.  The former replaces arachne's main running method for the gevent and threading runtimes, while the latter takes advantage of multiple phases that input has to go through for execution.
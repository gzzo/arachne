from arachne.base import Chooser
from arachne.utils import celery_output, strip_open, replace_params
from arachne.browser import Browser
from arachne.celery import celery
from collections import OrderedDict

name = 'sqli-scan'
def base_sqli_scan(url, browser_args):
	b = Browser(name, **browser_args)

	sqli_keys = [	['sql','syntax'],
					['syntax','error'],
					['sql', 'error'],
					['query', 'failed'],
					['incorrect', 'syntax']
				]

	r = b.go(url)

	if any( all(key in r.text for key in sub) for sub in sqli_keys):
		return url

@celery.task(name='arachne.scripts.scan_sqli')
def scan_sqli(url, browser_args, job_name, out_name):
	out = base_sqli_scan(url, browser_args)
	if out:
		celery_output.delay(out, name, job_name, out_name)

class BaseSqliScanner( Chooser ):
	def __init__(self):
		desc = 'Scans list of URLs for simple SQL injections.'
		super(BaseSqliScanner, self).__init__(name, desc)

	def init_common(self, cls, obj):
		cls.inn_base = inn_base

	def init_async(self, cls, obj):
		obj.core = scan_sqli

	def init_local(self, cls, obj):
		obj.core = base_sqli_scan

def inn_base(self):
	urls = strip_open(self.args.in_file)
	todo = []
	for url in urls:
		if '?' in url:
			todo.extend(replace_params(url, '\''))
	return todo

def main():
	s = BaseSqliScanner()
	s.start()

if __name__ == "__main__":
	main()
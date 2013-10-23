import os, argparse
from arachne.base import Chooser
from arachne.utils import celery_output, get_out_name, out_dir, strip_open
from arachne.browser import Browser
from arachne.celery import celery
from zipfile import ZipFile
from StringIO import StringIO
from os import path

name = 'alexa-scraper'
def base_scrape_alexa(url, browser_args, out_name, add_http):
	b = Browser(name, **browser_args)
	r = b.go(url)

	zip_file = StringIO(r.content)
	z = ZipFile(zip_file, 'r')
	csv_file = 'top-1m.csv'
	z.extract(csv_file, out_dir)

	file_path = path.join(out_dir, csv_file)
	lines = strip_open(file_path)

	out_path = path.join(out_dir, out_name)
	if add_http:
		os.remove(file_path)
		with open(out_path, 'w+') as f:
			for line in lines:
				print >> f, 'http://' + line.split(',')[1]
	else:
		try:
			os.rename(file_path, out_path)
		except Exception as e:
			pass

	return len(lines)


@celery.task(name='arachne.scripts.scrape_alexa')
def scrape_alexa(url, browser_args, job_name, out_name, add_http):
	base_scrape_alexa(url, browser_args, 
		get_out_name(name, job_name, out_name), add_http)

class BaseAlexaScraper( Chooser ):
	def __init__(self):
		desc = 'Scrape top one million sites ranked by Alexa'
		super(BaseAlexaScraper, self).__init__(name, desc, has_input=False)
		self.subparser.add_argument('-a','--add_http', action='store_true',
			help='Sites are normally outputted as google.com, this option saves the URLs with http:// prepended to them.')

	def init_common(self, cls, obj):
		cls.inn_target = inn_target

	def init_async(self, cls, obj):
		obj.core = scrape_alexa
		obj.base_args += [
			obj.args.add_http
		]

	def init_local(self, cls, obj):
		obj.core = base_scrape_alexa
		cls.out_base = out_base
		cls.out_format = out_format
		obj.base_args += [
			get_out_name(self.name, obj.args.job_name, obj.args.out_file),
			obj.args.add_http
		]

def out_format(self, item, out):
    return out

def out_base(self, item):
	self.status_good += item

def inn_target(self):
	self.input.append('http://s3.amazonaws.com/alexa-static/top-1m.csv.zip')

def main():
	s = BaseAlexaScraper()
	s.start()

if __name__ == "__main__":
	main()
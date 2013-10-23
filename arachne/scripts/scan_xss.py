from __future__ import absolute_import

from arachne.base import Chooser
from arachne.utils import celery_output, replace_params
from arachne.browser import Browser
from arachne.celery import celery
from arachne.scripts.check_keyword import base_check_keyword
from celery import group
from re import findall
from lxml import html

## taken from https://www.owasp.org/index.php/XSS_Filter_Evasion_Cheat_Sheet
vectors = [	"""'';!--"<SSX>=&{()}""" ]

name = 'xss-scanner'

def _scan_dom(js):
	## taken from https://code.google.com/p/domxsswiki/wiki/FindingDOMXSS
	sources = """(location\s*[\[.])|([.\[]\s*["']?\s*(arguments|dialogArguments|innerHTML|write(ln)?|open(Dialog)?|showModalDialog|cookie|URL|documentURI|baseURI|referrer|name|opener|parent|top|content|self|frames)\W)|(localStorage|sessionStorage|Database)"""
	sinks = """((src|href|data|location|code|value|action)\s*["'\]]*\s*\+?\s*=)|((replace|assign|navigate|getResponseHeader|open(Dialog)?|showModalDialog|eval|evaluate|execCommand|execScript|setTimeout|setInterval)\s*["'\]]*\s*\()"""

	matches = []
	source = findall(sources, js)
	if source:
		matches.extend(source)

	sink = findall(sinks, js)
	if sink:
		matches.extend(sink)
	return matches

def base_scan_dom(url, browser_args):
	b = Browser(name, **browser_args)

	r = b.go(url)

	if url.endswith('.js'):
		return _scan_dom(r.text)

	matches = []
	doc = html.document_fromstring(r.text)
	for elem in doc.xpath('//script'):
		matches.extend(_scan_dom(elem.text_content()))
	return matches	

def scan_js(url, browser_args):
	b = Browser(name, **browser_args)
	r = b.go(url)

	files = []
	for link in findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', r.text):
		if link.endswith('.js'):
			files.append(link)
	return files

@celery.task(name='arachne.scripts.scan_dom')
def scan_dom(url, browser_args, job_name, out_name):
	matches = base_scan_dom(url, browser_args)
	if matches:
		output = url + ' ||| {}'
		celery_output.delay(output.format(matches), name, job_name, out_name)

@celery.task(name='arachne.scripts.test_xss')
def test_xss(url, browser_args, job_name, out_name):
	out = base_check_keyword(url, browser_args, ['<SSX>'])
	if out:
		output = url + ' ||| {}'
		celery_output.delay(output.format(out), name, job_name, out_name)

@celery.task(name='arachne.scripts.scan_xss')
def scan_xss(url, browser_args, job_name, out_name):
	scan_dom.delay(url, browser_args, job_name, out_name)

	args = (browser_args, job_name, out_name)

	files = scan_js(url, browser_args)
	group(scan_dom.subtask( (link,) + args, kwargs,
		**scan_xss.request.delivery_info) for link in files)()

	if '?' in url:
		sites = []
		for vector in vectors:
			sites.extend(replace_params(url, vector, False))
		group(test_xss.subtask( (link,) + args, 
			**scan_xss.request.delivery_info) for link in sites)()

class BaseXssScanner( Chooser ):
	def __init__(self):
		desc = 'Scans for stored XSS in GET parameters and DOM based XSS from list of URLs'
		super(BaseXssScanner, self).__init__(name, desc)
		
	def init_async(self, cls, obj):
		obj.core = scan_xss

	def init_local(self, cls, obj):
		cls.xss_init = xss_init
		cls.xss_scan = xss_scan
		obj.phases = [obj.xss_init, obj.xss_scan]
		

def xss_init(self, my_link):
	output = my_link + ' ||| {}'

	matches = base_scan_dom(my_link, self.browser_args)
	if matches:
		self.output.append(output.format(matches))

	if '?' in my_link:
		for vector in vectors:
			self.to_input.extend(replace_params(my_link, vector, keep_original=False))
	files = scan_js(my_link, self.browser_args)
	self.to_input.extend(files)

def xss_scan(self, my_link):
	output = my_link + ' ||| {}'

	if my_link.endswith('.js'):
		matches = base_scan_dom(my_link, self.browser_args)
		if matches:
			self.output.append(output.format(matches))		
	else:	
		match =	base_check_keyword(my_link, self.browser_args, ['<SSX>'])
		if match:
			self.output.append(output.format(match))		

def main():
	s = BaseXssScanner()
	s.start()

if __name__ == "__main__":
	main()
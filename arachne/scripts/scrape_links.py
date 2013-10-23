from __future__ import absolute_import

import lxml.html
from arachne.base import Chooser, InObject
from arachne.utils import celery_output, BloomFilter
from arachne.browser import Browser
from arachne.celery import celery
from urlparse import urlparse
from collections import deque
from celery import group

name = 'link-scraper'
def base_link_scraper(link, browser_args, past, include_external):
	b = Browser(name, **browser_args)

	past.append(link)
	r = b.go(link)

	doc = lxml.html.document_fromstring(r.text)

	doc.make_links_absolute(r.url)
	root = urlparse(r.url).netloc
	output = []
	for element,attribute,uri,pos in doc.iterlinks():
		if attribute != 'href' or uri in past:
			continue
		past.append(uri)
		url_is_external = urlparse(uri).netloc != root
		include_external = include_external or not url_is_external

		if include_external:
			output.append(uri)
	return output

@celery.task(name='arachne.scripts.scrape_links')
def scrape_links(link, browser_args, job_name, out_name, depth, include_external, match, past=None):
	if not past:
		past = BloomFilter(capacity=3*10**(depth+3), error_rate=0.001)

	out = base_link_scraper(link, browser_args, past, include_external)
	if not out:
		return
	if depth:
		args = (browser_args, job_name,	out_name, depth-1, include_external, match)
		kwargs = {'past' : past}
		group(scrape_links.subtask((url,) + args, kwargs, 
			**scrape_links.request.delivery_info) for url in out)()

	if match:
		out = [url for url in out if any(x in url for x in match)]

	if out:
		celery_output.delay(out, name, job_name, out_name)

class BaseLinkScraper( Chooser ):
	def __init__(self):
		desc = 'Scrapes links from list of URLs'
		super(BaseLinkScraper, self).__init__(name, desc, has_match=True)

		self.subparser.add_argument('-d','--depth', type=int, default=0,
			help='Crawl links recursively up to DEPTH')
		self.subparser.add_argument('-e','--include_external', action='store_true',
			help='Include sites outside of netloc for scraping')

	## each chooser object must specify these two methods which initialize the 
	## respective base with the necessary arguments needed to run
	def init_async(self, cls, obj):
		obj.core = scrape_links
		obj.base_args += [
			obj.args.depth, 
			obj.args.include_external,
			obj.args.match
		]

	## these arguments are used for both the pooler and runner classes, which differ a lot
	## compared to the hopper used by celery tasks
	def init_local(self, cls, obj):
		cls.link_scraper = link_scraper	
		obj.past = deque()
		obj.phases = [obj.link_scraper]		
		obj.in_object['depth'] = obj.args.depth
		obj.base_args += [
			obj.past,
			obj.args.include_external
		]

## since we might have to do some slight recursion, we overwrite our standard run_base
## to take into account for the additional work
def link_scraper(self, my_link):
	try:
		out = base_link_scraper(my_link.item, *self.base_args)
	except Exception as e:
		return self.error_catch('scraping links', my_link, e)

	if my_link.depth:
		for link in out:
			self.add(InObject(link, depth=my_link.depth - 1))

	if self.args.match:
		out = [url for url in out if any(x in url for x in self.args.match)]
	self.output.extend(out)	

def main():
	s = BaseLinkScraper()
	s.start()

if __name__ == "__main__":
	main()
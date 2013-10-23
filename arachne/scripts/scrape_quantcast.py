import lxml.html
from arachne.base import Chooser
from arachne.utils import celery_output
from arachne.browser import Browser
from arachne.celery import celery

name = 'quantcast-scraper'
def base_scrape_quantcast(num, browser_args):
		b = Browser(name, **browser_args)
		url = 'http://www.quantcast.com/top-sites/US/{}'.format(num)
		r = b.go(url)
		
		site = lxml.html.document_fromstring(r.text)
		site.make_links_absolute(r.url)
		links = site.find_class('twoColumn')[0]

		output=[]
		for element,attribute,uri,pos in links.iterlinks():
			if attribute == 'href':
				output.append('http://' + element.text)
		return output

@celery.task(name='arachne.scripts.scrape_quantcast')
def scrape_quantcast(link, browser_args, job_name, out_name):
	out = base_scrape_quantcast(link, browser_args)
	if out:
		celery_output.delay(out, name, job_name, out_name)

class BaseQuantcastScraper( Chooser ):
	def __init__(self):
		desc = 'Scrapes top sites ranked by Quantcast'
		super(BaseQuantcastScraper, self).__init__(name, desc, has_input=False)
		
		self.subparser.add_argument('-r','--range',
			help='Number or range of numbers to scrape top sites in the hundreds. i.e., 2-5 will get the top 200 to 500 sites.')

	def init_common(self, cls, obj):
		cls.inn_target = inn_target

	def init_async(self, cls, obj):
		obj.core = scrape_quantcast

	def init_local(self, cls, obj):
		obj.core = base_scrape_quantcast

def inn_target(self):
	todo = [1]
	if self.args.range:
		range_nums = [int(x) for x in self.args.range.split('-')]
		todo = range_nums if len(range_nums) == 1 else xrange(range_nums[0],range_nums[1]+1)
		self.args.job_name += self.args.range
	self.input.extend(todo)

def main():
	s = BaseQuantcastScraper()
	s.start()

if __name__ == "__main__":
	main()
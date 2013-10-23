import lxml.html, re
from arachne.base import Chooser
from arachne.utils import celery_output
from arachne.browser import Browser
from arachne.celery import celery

name = 'proxy-scraper'
def base_scrape_proxy(num, browser_args):
	b = Browser(name, **browser_args)
	url = 'http://hidemyass.com/proxy-list/{}'.format(num)
	r = b.go(url)

	doc = lxml.html.document_fromstring(r.text)
	table = doc.get_element_by_id('listtable')
	rows = table.getchildren()[1:]

	ips = []
	for row in rows:
		columns = row.getchildren()
		port = columns[2].text_content().strip()
		info = columns[1].getchildren()[0].getchildren()
		style = lxml.html.tostring(info[0])

		bad_styles = []
		for css in style.splitlines()[1:-1]:
			if 'none' in css:
				bad_styles.append(css.split('{')[0][1:])

		ip = ''
		tricky_style = re.findall('<\/style>(\d{1,3})', style)
		if tricky_style:
			ip += tricky_style[0] + '.'
		for span in info[1:]:
			span_html = lxml.html.tostring(span)
		 	tricky_html = re.findall('(?:<\/span>|<\/div>)\.?(\d{1,3})', span_html)
			if tricky_html:
				ip += tricky_html[0] + '.'
			if 'none' not in span_html and not any(bad in span_html for bad in bad_styles):
				span_text = span.text_content()
				if re.search('\d', span_text):
					ip += span_text + '.'
		ips.append(ip[:-1])
	return ips

@celery.task(name='arachne.scripts.scrape_proxy')
def scrape_proxy(link, browser_args, job_name, out_name):
	out = base_scrape_proxy(link, browser_args)
	if out:
		celery_output.delay(out, name, job_name, out_name)

class BaseProxyScraper( Chooser ):
	def __init__(self):
		desc = 'Scrapes proxy list from hidemyass'
		super(BaseProxyScraper, self).__init__(name, desc, has_input=False)

		self.subparser.add_argument('-r', '--range',
			help='Number or range of numbers of page numbers to scrape')

	def init_common(self, cls, obj):
		cls.inn_target = inn_target

	def init_async(self, cls, obj):
		obj.core = scrape_proxy

	def init_local(self, cls, obj):
		obj.core = base_scrape_proxy

def inn_target(self):
	todo = [1]
	if self.args.range:
		range_nums = [int(x) for x in self.args.range.split('-')]
		todo = range_nums if len(range_nums) == 1 else xrange(range_nums[0],range_nums[1]+1)
		self.args.job_name += self.args.range
	self.input.extend(todo)

def main():
	s = BaseProxyScraper()
	s.start()

if __name__ == "__main__":
	main()
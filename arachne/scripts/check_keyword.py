from arachne.base import Chooser
from arachne.browser import Browser
from arachne.celery import celery
from arachne.utils import celery_output

name = 'keyword-checker'
def base_check_keyword(link, browser_args, keywords, check_url=False):
	b = Browser(name, **browser_args)
	r = b.go(link)

	if any(x in r.text for x in keywords):
		return r.url
	if check_url:
		if any(x in r.url for x in keywords):
			return r.url
	return ''

@celery.task(name='arachne.scripts.check_keyword')
def check_keyword(link, browser_args, job_name, out_name, keywords, check_url=False):
	out = base_check_keyword(link, browser_args, keywords, check_url)
	if out:
		celery_output.delay(out, name, job_name, out_name)

class BaseKeywordChecker( Chooser ):
	def __init__(self):
		desc = 'Check list of URLs if they contain keywords'
		super(BaseKeywordChecker, self).__init__(name, desc, has_match=True)

		self.subparser.add_argument('-r', '--check_url', action='store_true',
			help='Also check the URL for matching keywords, helpful for checking redirects')

	def init_common(self, cls, obj):
		obj.base_args += [
			obj.args.match,
			obj.args.check_url
		]

	def init_async(self, cls, obj):
		obj.core = check_keyword			

	def init_local(self, cls, obj):
		obj.core = base_check_keyword

def main():
	s = BaseKeywordChecker()
	s.start()

if __name__ == "__main__":
	main()
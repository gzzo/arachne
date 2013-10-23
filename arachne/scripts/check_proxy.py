from arachne.base import Chooser
from arachne.utils import celery_output
from arachne.browser import Browser
from arachne.celery import celery

name = 'proxy-checker'
def base_check_proxy(proxy, browser_args, target_site, target_key):
	b = Browser(name, change_proxy=False, max_retries=2, max_timeouts=2, **browser_args)

	bad = False
	try:
		r = b.go(target_site, proxy=proxy)
	except Exception as e:
		return

	if r.ok and target_key in r.text:
		return proxy

@celery.task(name='arachne.scripts.check_proxy')
def check_proxy(proxy, browser_args, job_name, out_name, target_site, target_key):
	out = base_check_proxy(proxy, browser_args, target_site, target_key)
	if out:
		celery_output.delay(out, name, job_name, out_name)

class BaseProxyChecker( Chooser ):
	def __init__(self):
		desc = 'Checks list of proxies to see if they can reach a target site'
		super(BaseProxyChecker, self).__init__(name, desc)

		self.subparser.add_argument('-a', '--target_site', default='http://www.google.com',
			help='URL for proxies to visit')
		self.subparser.add_argument('-k', '--target_key', default='google_favicon',
			help='Keyword to check in response.  Useful for proxies that may filter target site')

		self.args = self.subparser.parse_known_args()[0]
		if self.args.proxy_file:
			self.args.in_file = self.args.proxy_file
		
	def init_common(self, cls, obj):
		obj.base_args += [
			obj.args.target_site,
			obj.args.target_key
		]

	def init_async(self, cls, obj):
		obj.core = check_proxy

	def init_local(self, cls, obj):
		obj.core = base_check_proxy

def main():
	s = BaseProxyChecker()
	s.start()

if __name__ == "__main__":
	main()
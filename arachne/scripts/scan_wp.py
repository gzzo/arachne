from __future__ import absolute_import

from arachne.base import Chooser, InObject
from arachne.utils import celery_output
from arachne.browser import Browser
from arachne.celery import celery
from urlparse import urljoin
from celery import group

name = 'wp-scanner'
def base_find_wp(url):
	u = url.split('/')
	u_split = u[2].split('.')
	u_dom = u[0] + '//' + u[2]
	todo = [u_dom]
	if len(u_split) > 2:
	    todo.append(u[0] + '//' + '.'.join(['blog'] + u_split[1:]))
	else:
		todo.append(u_dom.replace('://','://blog.'))
	addtl = ['/blog/','/wp/','/wordpress/']
	[todo.append(u_dom + sub) for sub in addtl]

	return todo

def base_scan_wp(url, browser_args):
	WP_LOGIN = 'wp-login.php'
	WP_VALID = ['loginform']
	WP_CAPCH = ['cptch_block']

	b = Browser(name, **browser_args)

	if not url.endswith(WP_LOGIN):
		url = urljoin(url, WP_LOGIN)
	try:
		r = b.go(url)
	except Exception as e:
		return

	if r.ok and all(x in r.text for x in WP_VALID) and not any(x in r.text for x in WP_CAPCH):
		return url

@celery.task(name='arachne.scripts.scan_wp')
def scan_wp(url, browser_args, job_name, out_name, first=True):
	out = base_scan_wp(url, browser_args)
	if out:
		celery_output.delay(out, name, job_name, out_name)
	elif first:
		args = (browser_args, job_name, out_name)
		kwargs = {'first' : False}
		group(scan_wp.subtask( (link,) + args, kwargs, 
			**scan_wp.request.delivery_info) for link in base_find_wp(url))()

class BaseWpScanner( Chooser ):
	def __init__(self):
		desc = 'Scans a domain for a wordpress login page'
		super(BaseWpScanner, self).__init__(name, desc)

	def init_async(self, cls, obj):
		obj.core = scan_wp

	def init_local(self, cls, obj):
		cls.wp_scanner = wp_scanner
		obj.phases = [obj.wp_scanner]
		obj.in_object['first'] = True

def wp_scanner(self, my_link):
	try:
		match = base_scan_wp(my_link.item, self.browser_args)
	except Exception as e:
		return self.error_catch('scanning wp', my_link, e)		

	if match:
		self.output.append(match)
	elif my_link.first:
		for link in base_find_wp(my_link.item):
			self.add(InObject(link, first=False))

def main():
	s = BaseWpScanner()
	s.start()

if __name__ == "__main__":
	main()
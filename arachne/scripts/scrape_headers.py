from arachne.base import Chooser
from arachne.utils import celery_output
from arachne.browser import Browser
from arachne.celery import celery
from urlparse import urlparse
from json import dumps

name = 'header-scraper'
def base_scrape_headers(link, browser_args, match):
    b = Browser(name, **browser_args)

    r = b.go(link)
    
    if not match:
        return dict(r.headers)
    matches = {}
    for field in match:
        value = r.headers.get(field)
        if value:
            matches[field] = value
    return matches

@celery.task(name='arachne.scripts.scrape_headers')
def scrape_headers(link, browser_args, job_name, out_name, match):
    out = base_scrape_headers(link, browser_args, match)
    if out:
        celery_output.delay(dumps([link, out], indent=4), name, job_name, out_name)

class BaseHeaderScraper( Chooser ):
    def __init__(self):
        desc = 'Scrapes headers from list of URLs'
        super(BaseHeaderScraper, self).__init__(name, desc, has_match=True)

    def init_common(self, cls, obj):
        obj.base_args += [self.args.match]

    def init_async(self, cls, obj):
        obj.core = scrape_headers

    def init_local(self, cls, obj):
        cls.out_format = out_format
        obj.core = base_scrape_headers

def out_format(self, item, out):
    return dumps([item, out], indent=4)

def main():
    s = BaseHeaderScraper()
    s.start()

if __name__ == "__main__":
    main()
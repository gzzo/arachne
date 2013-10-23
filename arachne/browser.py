import requests, random, socket

## all scripts use this as a browser, it is runs on requests but includes features such as
## retrying requests when they fail, changing proxies when requests fail, randomizing
## user agents, and by default runs on a requests session which keeps track of cookies across requests
class Browser(object):    
    def __init__(self, name='', cookies=True, proxy_file=None, log_errors=False,
                 ua_file=None, timeout=10, max_retries=3, max_timeouts=5, change_proxy=True):
        self.def_ua = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'
        self.name = name
        self.timeout = timeout
        self.log_errors = log_errors
        self.max_retries = max_retries
        self.max_timeouts = max_timeouts
        self.session = requests.Session() if cookies else requests
        self.change_proxy = change_proxy
        self.ua = None
        if ua_file:
            with open(ua_file, 'r') as f:
                self.ua = [x.strip() for x in f.readlines()]
            self.def_ua = self.ua[0]

        self.proxy = None
        if proxy_file:
            with open(proxy_file,'r') as f:
                self.proxy = [x.strip() for x in f.readlines()]

        self.headers = {'User-Agent': self.def_ua,
                'Accept'    : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language'   : 'en-US,en;q=0.5',
                'Accept-Encoding'   : 'gzip, deflate'}

    def del_proxy(self, proxy):
        self.proxy.remove(proxy)
        with open('{}-bad'.format(self.proxy_file),'a+') as f:
            f.write('{}\n'.format(proxy))

    def get_proxy(self, past=None):
        if not self.proxy:
            return None
        if past:
            pospx = [x for x in self.proxy if x not in past]
            if not pospx:
                ## there could be a possibility that we have already tried all proxies in our 
                ## list unsuccesfully, it might be a good idea to raise an exception here
                ## since it will get caught and won't interrupt threads, but this works for now
                return random.choice(self.proxy)
            return random.choice(pospx)
        else:
            return random.choice(self.proxy)

    def go(self, url, proxy=None, data=None, cookies=None):
        retry = 0
        timeout = 0
        past_proxy = []
        past_error = []
        while retry < self.max_retries and timeout < self.max_timeouts:
            if self.ua:
                    self.headers['User-Agent'] = random.choice(self.ua)
            proxy_d = None
            if self.proxy or proxy:
                proxy = proxy if proxy else self.get_proxy()
                past_proxy.append(proxy)
                if 'http' not in proxy:
                    ## requests 2.0.0 requires explicits schemas in proxies
                    proxy = 'http://' + proxy
                proxy_d = {'http' : proxy, 'https' : proxy}
            method = 'post' if data else 'get'
            try:                
                return self.session.request(method, url, data=data, headers=self.headers, 
                    cookies=cookies, proxies=proxy_d, allow_redirects=True, timeout=self.timeout)
            except (requests.exceptions.Timeout, socket.timeout) as e:
                past_error.append(e)
                timeout += 1
                proxy = self.error_catch(e,past_proxy)
            except (requests.exceptions.RequestException, socket.error) as e:
                past_error.append(e)
                retry += 1
                proxy = self.error_catch(e, past_proxy)
        ## this is necessary to each script doesn't have to check whether or not it actually
        ## got a response back, it just catches an exception instead
        raise Exception('Failed to load {} -- {}'.format(url,past_error))

    def error_catch(self, error, past):
        adtl = ''
        newproxy = None
        if self.change_proxy and self.proxy:
            newproxy = self.get_proxy(past)
            adtl = ' | Changing proxy: {} - {}'.format(past[-1],newproxy)
        elif past:
            newproxy = past[0]
        if self.log_errors:
            print('{} caught error: {}'.format(self.name,error,adtl))
        return newproxy
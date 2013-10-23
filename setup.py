from setuptools import setup, find_packages

setup(
    name = "arachne",
    version = "0.4",
    packages = find_packages(),

    install_requires = ['requests==2.0.0', 'gevent==0.13.8', 'celery==3.0.24', 'lxml==3.2.3', 'pybloom==1.1'],

    package_data = {
        'arachne.scripts.defaults' : ['wp_pass']
    },

    author = "Guido Rainuzzo",
    author_email = "guidorainuzzo@gmail.com",
    description = "framework for web testing on multiple runtimes",
    license = "GPL",
    keywords = "scraping scanning testing",
    url = "https://github.com/gzzo/arachne", 

    entry_points = {
        'console_scripts': [
            'scrape_links = arachne.scripts.scrape_links:main',
            'scrape_headers = arachne.scripts.scrape_headers:main',
            'scrape_alexa = arachne.scripts.scrape_alexa:main',
            'scrape_quantcast = arachne.scripts.scrape_quantcast:main',
            'scrape_proxy = arachne.scripts.scrape_proxy:main',
            'scan_xss = arachne.scripts.scan_xss:main',
            'scan_sqli = arachne.scripts.scan_sqli:main',
            'scan_rlfi = arachne.scripts.scan_rlfi:main',
            'scan_wp = arachne.scripts.scan_wp:main',
            'exploit_sqli_dump = arachne.scripts.exploit_sqli_dump:main',
            'exploit_wp_leaguemanager = arachne.scripts.exploit_wp_leaguemanager:main',
            'exploit_wp_brute = arachne.scripts.exploit_wp_brute:main',
            'check_proxy = arachne.scripts.check_proxy:main',
            'check_keyword = arachne.scripts.check_keyword:main',
            'smtp_send = arachne.scripts.smtp_send:main'
        ],
    }
)
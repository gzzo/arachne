import socket, ssl
from arachne.base import Chooser
from arachne.browser import Browser
from arachne.utils import strip_open
from smtplib import SMTP, SMTP_SSL
from random import choice
from arachne.celery import celery

name = 'smtp-send'
def base_smtp_send(item):
    usetls, smtp_server, mail_from, mail_pwd, name_from, mail_to, name_to, subject, body = item
    
    message = """From: {} <{}>
To: {} <{}>
Subject: {}

{}
""".format(name_from, mail_from, name_to, mail_to, subject, body.replace('\\n','\n'))
    
    temp = smtp_server.split(':')
    smtp_host = temp[0]
    if usetls:
        smtp_port = 587
    else:
        smtp_port = 465    
    if len(temp) > 1:
        smtp_port = temp[1]

    server = SMTP(smtp_server, smtp_port)

    if usetls:
        server.ehlo()
        server.starttls()
        server.ehlo
    
    server.login(mail_from, mail_pwd)
    server.sendmail(mail_from, mail_to, message)
    server.quit()

    return True

@celery.task(name='arachne.scripts.smtp_send')
def smtp_send(item):
    base_smtp_send(item)

# class ProxySMTP( SMTP ):
#     def __init__(self, usetls=False, host='', port=465, paddr='',pport=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
#         self.pro = paddr
#         self.ppo = pport
#         self.timeout = timeout
#         self.esmtp_features = {}
#         self.default_port = port
#         (code, msg) = self.connect(host,port)

#         super().__init__(ProxySMTP, self)

#     def _get_socket(self, host, port, timeout):
#         s = socks.socksocket()
#         s.setproxy(socks.PROXY_TYPE_HTTP_NO_TUNNEL, self.pro, self.ppo, True)
#         s.connect((host,port))
#         s = ssl.wrap_socket(s)
#         self.file = SSLFakeFile(s)
#         return s

class BaseSMTPSender( Chooser ):
    def __init__(self):
        desc = 'Send emails through SMTP to list of addresses from random logins'
        super(BaseSMTPSender, self).__init__(name, desc)

        self.subparser.add_argument('-l', '--logins_file',
            help='List of logins to send emails from.  Format: usetls:server:login:password:name.\
                                Example: 0:smtp.yahoo.com:email@yahoo.com:mypassword:My Name.\
                                With TLS: 1:smtp.gmail.com:email@gmail.com:mypassword:my gmail.')
        self.subparser.add_argument('-e', '--subjects_file',
            help='List of subjects to send, chosen randomly')
        self.subparser.add_argument('-b', '--bodies_file',
            help='List of messages to send, chosen randomly')
    
    def init_common(self, cls, obj):
        cls.inn_base = inn_base

    def init_async(self, cls, obj):
        obj.core = smtp_send
        obj.base_args = []

    def init_local(self, cls, obj):
        obj.core = base_smtp_send
        obj.base_args = []

def out_base(self, my_item):
    self.status_good += 1

def inn_base(self):
        sends = strip_open(self.args.in_file)
        logins = strip_open(self.args.logins_file)
        subjects = strip_open(self.args.subjects_file)
        bodies = strip_open(self.args.bodies_file)

        todo = []
        for send in sends:
            mail_to = send.split(':')
            login = choice(logins).split(':')
            subject = choice(subjects)
            body = choice(bodies)

            usetls = True if login[0] == '1' else False
            info = [usetls, login[1], login[2], login[3], login[4], mail_to[0], mail_to[1], subject, body]
            todo.append(info)
        return todo

def main():
    s = BaseSMTPSender()
    s.start()

if __name__ == "__main__":
    main()
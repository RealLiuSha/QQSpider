#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   Author  :   itchenyi
#   E-mail  :   itchenyi@gmail.com
#   Date    :   15/11/14 19:17:23
#   Desc    :
#
from __future__ import unicode_literals
import os
import re
import sys
import json
import time
import atexit
import random
import grequests
from signal import SIGTERM
from datetime import datetime


class Daemon:
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        try:
            pid = os.fork()
            if pid > 0:
                #: exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        try:
            with file(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
                os.remove(self.pidfile)
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return

        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            print str(err)
            sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        run
        """


class Counter:
    def __init__(self):
        self.count = random.randint(0, 10000000)

    def get(self):
        self.count += 1
        return self.count


class Client(Counter):
    def __init__(self, mail_info):
        Counter.__init__(self)
        self.session = grequests.Session()
        self.msg_id = self.count
        self.mail_info = mail_info
        self.params = {
            'time': time.time(),
            'appid': '0',
            'msgid': '0',
            'clientid': random.randint(1, 10000000),
            'ptwebqq': '',
            'vfwebqq': '',
            'psessionid': '',
            'friendList': {},
            'referer': 'http://d.web2.qq.com/proxy.html?v=20130916001&callback=1&id=2',
            'smartqqurl': 'http://w.qq.com/login.html'
        }
        self.uin2tuin = 'http://s.web2.qq.com/api/get_friend_uin2?tuin={0}&type=1&vfwebqq={1}'
        self.session.headers = {
            'Accept': 'application/javascript, */*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/31.0.1650.48 Safari/537.36 QQBrowser/8.2.4258.400'
        }
        self.session.verify = True

    @classmethod
    def get_html_value(cls, content, regex):
        value = re.search(regex, content)
        if value is None:
            return None
        return value.group(1)

    @classmethod
    def combine_msg(cls, content, msg_txt=u""):
        if isinstance(content[1:], list):
            #: item is picture
            for item in content[1:]:
                if isinstance(item, list):
                    if item[0] == 'offpic' or item[0] == 'cface':
                        msg_txt += '[图片]'

                    if item[0] == 'face':
                        msg_txt += '[表情]'

                if isinstance(item, unicode):
                    msg_txt += item

        return msg_txt

    def write_msg(self, path, msg, mail=False, content=None):
        if os.path.exists(os.path.split(path)[0]):
            print >> open(path, "a+"), msg
        else:
            raise IOError("やめて %s" % path)

        if mail and content:
            self.send_mail(content)

    def send_mail(self, content):
        from smtplib import SMTP_SSL as SMTP
        from email.mime.text import MIMEText

        me = "QQSpider<{_user}@{_postfix}>".format(_user=self.mail_info['mail_user'],
                                                   _postfix=self.mail_info['mail_postfix'])
        msg = MIMEText("<h5>QQSpider Error: Number is {0}</h5><br /><span>by jackliu</span>".format(content),
                       _subtype='html', _charset='utf8')
        msg['Subject'] = "QQSpider Warning"
        msg['From'] = me
        msg['To'] = ";".join(self.mail_info['mail_to_list'].split(','))
        try:
            smtp = SMTP()
            smtp.connect(self.mail_info['mail_host'], self.mail_info['mail_port'])
            smtp.login("{0}@{1}".format(self.mail_info['mail_user'],
                       self.mail_info['mail_postfix']), self.mail_info['mail_pass'])

            smtp.sendmail(me, self.mail_info['mail_to_list'].split(','), msg.as_string())
            smtp.close()
        except Exception as e:
            print(e)
            exit(128)

    def uin_to_account(self, tuin):
        if tuin not in self.params['friendList']:
            try:
                info = json.loads(self.session.get(self.uin2tuin.format(
                    tuin, self.params['vfwebqq']
                ), headers={"Referer": self.params['referer']}).content)

                if info['retcode'] != 0:
                    raise ValueError(info)

                #: get uin account info
                self.params['friendList'][tuin] = info['result']['account']

            except Exception as e:
                print(e)

        return self.params['friendList'][tuin]

    def save_qrcode(self, filename, url):
        with open(filename, 'wb') as handle:
            response = self.session.get(url, stream=True)
            if not response.ok:
                print "shit"
                exit()

            for block in response.iter_content(1024):
                handle.write(block)

    def up_time(self):
        last_time = (time.time() - self.params['time'])
        self.params['time'] = time.time()
        return str(round(last_time, 3))


class QQ(Client, Daemon):

    def __init__(self, qq_number, logs_path, qrcode_path, data_path, mail_info):
        Client.__init__(self, mail_info=mail_info)
        Daemon.__init__(self, pidfile="/tmp/qq_%s.pid" % qq_number)
        self.count = 0
        self.byebye = 0
        self.try_count = 5
        self.login_err = 1
        self.nickname = None
        self.result = None
        self.timeout = 80
        self.qq_number = qq_number
        self.logs_path = logs_path + "/qq_{0}.log".format(qq_number)
        self.data_path = data_path + "/qq_{0}.data".format(qq_number)
        self.qrcode_path = qrcode_path + "/qrcode_{0}.png".format(qq_number)
        self.qlogin = 'http://d.web2.qq.com/channel/login2'
        self.poll2 = 'http://d.web2.qq.com/channel/poll2'
        self.poll2_data = '{{"ptwebqq":"{0}","clientid":{1},"psessionid":"{2}","key":""}}'
        self.qlogin_data = '{{"ptwebqq":"{0}","clientid":{1},"psessionid":"{2}","status":"online"}}'
        self.qrcode = 'https://ssl.ptlogin2.qq.com/ptqrshow?appid={_app_id}&e=0&l=L&s=8&d=72&v=4'
        self.qrcode_verify = ('https://ssl.ptlogin2.qq.com/ptqrlogin?webqq_type=10&remember_uin=1'
                              '&login2qq=1&aid={0}&u1=http%3A%2F%2Fw.qq.com%2Fproxy.html%3Flogin2'
                              'qq%3D1%26webqq_type%3D10&ptredirect=0&ptlang=2052&daid=164&from_ui=1'
                              '&pttype=1&dumy=&fp=loginerroralert&action=0-0-{1}&mibao_css={2}'
                              '&t=undefined&g=1&js_type=0&js_ver={3}&login_sig={4}')

    def login(self):
        init_url = self.get_html_value(
                        self.session.get(self.params['smartqqurl']).content, r'\.src = "(.+?)"')

        #: login + var name
        _html = self.session.get(init_url + '0').content

        #: _app_id useless
        self.get_html_value(_html, r'g_appid\s*=\s*encodeURIComponent\s*\("(\d+)"')
        _sign = self.get_html_value(_html, r'g_login_sig\s*=\s*encodeURIComponent\s*\("(.+?)"\)')
        _js_ver = self.get_html_value(_html, r'g_pt_version\s*=\s*encodeURIComponent\s*\("(\d+)"\)')
        _mibao_css = self.get_html_value(_html, r'g_mibao_css\s*=\s*encodeURIComponent\s*\("(.+?)"\)')
        _start_time = (int(time.mktime(datetime.utcnow().timetuple())) * 1000)

        while True:
            self.count += 1
            self.save_qrcode(self.qrcode_path, self.qrcode.format(_app_id=self.params['appid']))

            while True:
                _html = self.session.get(self.qrcode_verify.format(
                    self.params['appid'], ((int(time.mktime(datetime.utcnow().timetuple())) * 1000) - _start_time),
                    _mibao_css, _js_ver, _sign), headers={"Referer": self.params['referer']}
                ).content

                self.result = _html.decode('utf-8').split("'")
                if self.result[1] == '65' or self.result[1] == '0':
                    break

                time.sleep(2)

            if self.result[1] == '0' or self.count > 5:
                break

        if self.result[1] != '0':
            raise ValueError("RetCode = %s" % self.result['retcode'])

        print "Login Sucess"
        self.up_time()
        #: Assignment current nickname
        self.nickname = self.result[11]

        self.session.get(self.result[5])
        self.params['ptwebqq'] = self.session.cookies['ptwebqq']

        while self.login_err != 0:
            try:
                _html = self.session.post(self.qlogin, data={'r': self.qlogin_data.format(
                    self.params['ptwebqq'], self.params['clientid'], self.params['psessionid']
                )}, headers={"Referer": self.params['referer']}).content

                self.result = json.loads(_html)
                self.login_err = 0
            except Exception as e:
                self.login_err += 1
                self.write_msg(self.logs_path, "Login Field....retrying.... \n{0}".format(e))

        if self.result['retcode'] != 0:
            raise ValueError("Login Retcode=%s" % str(self.result['retcode']))

        self.params['vfwebqq'] = self.result['result']['vfwebqq']
        self.params['psessionid'] = self.result['result']['psessionid']
        self.params['msgid'] = int(random.uniform(20000, 50000))
        self.write_msg(self.logs_path, "Login({0}) Sucess, nickname({1})".format(
                       self.result['result']['uin'], self.nickname))

    def msg_handler(self, msg):
        for item in msg:
            msg_type = item['poll_type']

            #: message and sess_message no opration
            if msg_type == 'message' or msg_type == 'sess_message':
                pass

            if msg_type == 'group_message':
                text = self.combine_msg(item['value']['content'])
                date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['value']['time']))
                gid = item['value']['info_seq']
                qid = self.uin_to_account(str(item['value']['send_uin']))
                self.write_msg(self.data_path, (text, date, gid, qid, self.qq_number))

            if msg_type == 'kick_message':
                raise Exception(item['value']['reason'])

    def check_message(self):
        try:
            _html = self.session.post(self.poll2, data={'r': self.poll2_data.format(
                self.params['ptwebqq'], self.params['clientid'], self.params['psessionid']
            )}, headers={"Referer": self.params['referer']}, timeout=self.timeout).content
        except Exception as _timeout:
            self.write_msg(self.logs_path, "check_message:\n[{0}]".format(_timeout),
                           mail=True, content=self.qq_number)
            self.stop()

        self.write_msg(self.logs_path, "Pull message... info[{qq},{time}]".format(
                       qq=self.nickname, time=datetime.now()))
        try:
            result = json.loads(_html)
        except Exception as e:
            self.write_msg(self.logs_path, "Pull message failed, retrying!\n{0}".format(e))
            return self.check_message()

        return result

    def run(self):
        self.login()
        while True:
            time.sleep(0.55)
            if self.byebye < 5:
                result = self.check_message()
            else:
                self.write_msg(self.logs_path, "やめて", mail=True, content=self.qq_number)
                self.stop()

            #: Post data format error
            if result['retcode'] == 100006:
                self.byebye += 1

            #: No Message
            elif result['retcode'] == 102:
                self.byebye = 0

            #: Update ptwebqq value
            elif result['retcode'] == 116:
                self.params['ptwebqq'] = result['p']
                self.byebye = 0

            #: やめて
            elif result['retcode'] == 0:
                self.msg_handler(result['result'])
                self.byebye = 0

            else:
                self.byebye += 1


if __name__ == '__main__':
    optional = ['start', 'stop', 'restart', 'debug']

    from argparse import ArgumentParser
    parser = ArgumentParser(prog='QQSpider')
    parser.add_argument('--number', required=True, help='qq number')
    parser.add_argument('--action', required=True, help='start|stop|restart|debug')
    args = parser.parse_args()

    if args.action not in optional:
        print "optional やめて"
        sys.exit(128)

    from ConfigParser import ConfigParser
    CONFIG_PATH = os.environ.get('QQ_CONFIG_PATH') or './config.ini'

    config = ConfigParser()
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
    else:
        print "CONFIG_PATH やめて"

    #: create not exists dir
    for _, _path in set(config.items('path')):
        if not os.path.exists(_path):
            os.makedirs(_path)

    daemon = QQ(qq_number=args.number,
                logs_path=config.get('path', 'logs'),
                qrcode_path=config.get('path', 'qrcode'),
                data_path=config.get('path', 'data'),
                mail_info=dict(config.items('smtp')))

    if 'start' == args.action:
        daemon.start()
    elif 'stop' == args.action:
        daemon.stop()
    elif 'restart' == args.action:
        daemon.restart()
    elif 'debug' == args.action:
        daemon.run()
    else:
        print "やめて"

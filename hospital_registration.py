import base64
import json
import logging
import re
import sys
import time
import unicodedata

import requests


def printf(*args):
    """
    格式化打印
    :param args: list
    :return: None
    """
    width = [5, 25, 50, 10, 10]

    def wide_chars(s):
        if not isinstance(s, str):
            s = str(s)
        return sum(unicodedata.east_asian_width(x) in ('F', 'W') for x in s)

    fmt_str = '|'.join(['{%s:<%s}' % (i, width[i] - wide_chars(j)) for i, j in enumerate(args)])
    print(fmt_str.format(*args))
    return


class Registration:
    def __init__(self):
        self.mobile_no = ''  # 手机号码
        self.password = ''  # 密码
        self.duty_date = ''  # 挂号日期
        self.hospital_id = ''  # 医院ID
        self.department_id = ''  # 科室ID
        self.duty_code = ''  # 1:上午 2:下午
        self.medicare_card_id = ''  # 社保卡号
        self.name = ''  # 姓名
        self.auto_choose = True  # 是否服从系统分配
        self.phone_rest_addr = None  # REST SMS Gateway 地址

        self.doctor = {}  # 选定的医生
        self.patient_id = ''  # 就诊人ID
        self.start_time = 0  # 抢号开始时间戳

        # URL
        self.domain = 'http://www.114yygh.com'
        self.login_url = self.domain + '/quicklogin.htm'  # 登录
        self.part_duty_url = self.domain + '/dpt/partduty.htm'  # 获取号源信息
        self.send_order_url = self.domain + '/v/sendorder.htm'  # 发送短信验证码
        self.confirm_url = self.domain + '/order/confirmV1.htm'  # 挂号
        self.appoint_url = self.domain + '/dpt/appoint/{0}-{1}.htm'  # 预约信息页
        self.patient_form_url = self.domain + '/order/confirm/{0}-{1}-{2}-{3}.htm'  # 就诊人预约页

        # requests初始化
        self.session = requests.Session()
        self.session.mount(self.domain, requests.adapters.HTTPAdapter(max_retries=3))
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)'
        })

    def request(self, method, url, **kwargs):
        """
        请求
        :param method: string: 'get' or 'post'
        :param url: string
        :param kwargs: Optional arguments that ``request`` takes
        :return: requests.Response
        """
        if method == 'post':
            response = self.session.post(url, **kwargs)
        else:
            response = self.session.get(url, **kwargs)

        if response.status_code == 200:
            self.session.headers.update(Referer=response.url)
        return response

    def load_conf(self, config_path):
        """
        载入配置文件
        :param config_path: string
        :return: None
        """
        with open(config_path, 'r') as f:
            data = json.load(f)
            self.mobile_no = base64.b64encode(data.get('username', '').encode())
            self.password = base64.b64encode(data.get('password', '').encode())
            self.duty_date = data.get('dutyDate', '')
            self.hospital_id = data.get('hospitalId')
            self.department_id = data.get('departmentId')
            self.duty_code = data.get('dutyCode')
            self.medicare_card_id = data.get('medicareCardId', '').upper()
            self.name = data.get('name', '')
            self.auto_choose = data.get('autoChoose', True)
            self.phone_rest_addr = data.get('phoneRESTAddr')

            logging.info('配置加载完成')
            logging.debug('config: ' + str(data))
        if not all([self.mobile_no, self.password, self.hospital_id, self.department_id, self.duty_code]):
            logging.error('必选配置项有误，请重新修改')
            sys.exit()
        return

    def get_duty_time(self):
        """
        获取放号时间
        :return: None
        """
        url = self.appoint_url.format(self.hospital_id, self.department_id)
        res = self.request('get', url)
        data = res.text

        # 每日更新号源时间
        m = re.search(r'<span>更新时间：</span>每日(?P<refreshTime>\d{1,2}:\d{2})更新', data)
        refresh_time = m.group('refreshTime')
        logging.debug('更新时间: ' + refresh_time)

        # 预约周期
        m = re.search(r'<span>预约周期：</span>(?P<appointDay>\d+)<script', data)
        appoint_day = m.group('appointDay')
        logging.debug('预约周期: ' + appoint_day)
        today = time.time()
        if self.duty_date == '':
            self.duty_date = time.strftime('%Y-%m-%d', time.localtime(today + int(appoint_day) * 24 * 3600))
        logging.info('挂号日期为: ' + self.duty_date + (' 上午' if self.duty_code == '1' else ' 下午'))

        # 计算挂号当天的放号时间
        c_time = time.strptime(self.duty_date + ' ' + refresh_time, '%Y-%m-%d %H:%M')
        self.start_time = time.mktime(c_time) - int(appoint_day) * 24 * 3600
        logging.info('放号时间为: ' + time.strftime('%Y-%m-%d %H:%M', time.localtime(self.start_time)))
        return

    def auth_login(self):
        """
        登录
        :return: bool
        """
        logging.info('开始登录')
        args = dict(mobileNo=self.mobile_no,
                    password=self.password,
                    yzm='',
                    isAjax=True)
        res = self.request('post', self.login_url, data=args)
        logging.debug('response: ' + res.text)
        try:
            data = res.json()
            if data.get('code') == 200:
                logging.info('登录成功')
                return True
            else:
                logging.error(data.get('msg'))
                return False
        except Exception as e:
            logging.error('登录失败 %s', e)
            return False

    def choose_doctor(self):
        """
        选择医生
        :return: bool
        """
        logging.debug('当前挂号日期: ' + self.duty_date)
        args = dict(hospitalId=self.hospital_id,
                    departmentId=self.department_id,
                    dutyCode=self.duty_code,
                    dutyDate=self.duty_date,
                    isAjax=True)
        res = self.request('post', self.part_duty_url, data=args)
        logging.debug('response: ' + res.text)
        try:
            data = res.json()
            if data.get('code') == 200:
                duty_lst = data.get('data')
            else:
                duty_lst = []

            if len(duty_lst) == 0:  # 还未放号
                return False
            else:
                flag = None
                printf('序号', '医生', '擅长', '医事服务费', '剩余号')
                for index, item in enumerate(duty_lst):  # 打印号源列表
                    printf(index, item.get('doctorName'), item.get('skill'), item.get('totalFee'),
                           item.get('remainAvailableNumber'))
                    if item.get('remainAvailableNumber') > 0:
                        flag = index
                if flag and not self.auto_choose:
                    while True:
                        value = input('请按序号选择医生: ')
                        if value.isdigit() and 0 <= int(value) < len(duty_lst) \
                                and duty_lst[int(value)].get('remainAvailableNumber') > 0:
                            flag = int(value)
                            break
                        else:
                            logging.info('输入的序号有误，请重新输入')

                if flag is not None:
                    logging.info('选中: ' + duty_lst[flag].get('doctorName'))
                    self.doctor = duty_lst[flag]
                    return True
                else:
                    self.doctor = None
                    return False  # 号已抢完
        except Exception as e:
            logging.error('选择失败 %s', e)
            return False

    def get_patient_id(self):
        """
        获取就诊人ID
        :return: string or None
        """
        url = self.patient_form_url.format(self.hospital_id, self.department_id,
                                           self.doctor.get('doctorId'), self.doctor.get('dutySourceId'))
        res = self.request('get', url)
        data = res.text
        m = re.search(r'<div class="personnel.+" name="(?P<patientId>\d+)">.+<span class="name">' + self.name,
                      data)
        if m is None:
            logging.error('获取就诊人ID失败')
            return None
        else:
            self.patient_id = m.group('patientId')
            logging.info('就诊人ID: ' + self.patient_id)
            return self.patient_id

    def trigger_sms_verify_code(self):
        """
        触发短信验证码
        :return: bool
        """
        res = self.request('post', self.send_order_url, data='')
        logging.debug('response: ' + res.text)
        try:
            data = res.json()
            if data.get('code') == 200:
                logging.info('触发验证码成功')
                return True
            else:
                logging.error(data.get('msg'))
                return False
        except Exception as e:
            logging.error('触发短信验证码失败 %s', e)
            return False

    def fetch_sms_verify_code(self):
        """
        读取短信验证码
        :return: string or None
        """
        if not self.phone_rest_addr:
            return input('请输入短信验证码: ')

        resp = requests.get("http://{}/v1/sms/".format(self.phone_rest_addr))
        resp.raise_for_status()
        body = resp.json()

        for message in body["messages"]:
            if time.time() - int(message["timestamps"]["delivery"]) / 1000 > 60:
                continue
            if "114预约挂号" in message["body"] and "短信验证码" in message["body"]:
                code_re = re.search(r'\d{6}', message["body"])
                if code_re:
                    return code_re.group()

    def get_register(self):
        """
        挂号
        :param sms_code: string
        :return: bool
        """
        retries = 60 if self.phone_rest_addr else 3
        for _ in range(retries):
            sms_code = self.fetch_sms_verify_code()
            if not sms_code:
                logging.info("读取验证码失败，1s 后重试")
                time.sleep(1)
                continue
            logging.info("读取验证码成功 %s", sms_code)

            args = dict(dutySourceId=str(self.doctor.get('dutySourceId')),
                        hospitalId=self.hospital_id,
                        departmentId=self.department_id,
                        doctorId=str(self.doctor.get('doctorId')),
                        patientId=self.patient_id,
                        hospitalCardId='',
                        medicareCardId=self.medicare_card_id,
                        reimbursementType='1' if self.medicare_card_id else '10',
                        smsVerifyCode=sms_code,
                        childrenBirthday='',
                        isAjax=True)
            res = self.request('post', self.confirm_url, data=args)
            logging.debug('response: ' + res.text)
            try:
                data = res.json()
                if data.get('code') == 1:
                    logging.info('挂号成功')
                    return True
                else:
                    logging.error(data.get('msg'))
            except Exception as e:
                logging.error('挂号失败 %s', e)

        return False

    def run(self, config_path):
        """
        主函数
        :param config_path: string
        :return: None
        """
        self.load_conf(config_path)
        self.get_duty_time()
        now = time.time()
        if now < self.start_time - 30:  # 判断是否处于放号时间的前30秒之前
            seconds = int(self.start_time - now - 30)
            logging.info(str(seconds) + '秒后开始运行')
            time.sleep(seconds)
        if self.auth_login():
            while True:
                if self.choose_doctor():
                    if self.get_patient_id():
                        if self.trigger_sms_verify_code():
                            res = self.get_register()
                            if res:
                                break
                    time.sleep(1)
                else:
                    if self.doctor == {}:
                        logging.info('等待放号中')
                        time.sleep(1)
                    else:
                        logging.info('号已抢完')
                        break
        return


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename='reg_{0}.log'.format(int(time.time())),
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    reg = Registration()
    reg.run('./config.json')

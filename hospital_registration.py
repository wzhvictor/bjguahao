import json
import logging
import re
import sys
import time

import requests


class Registration:
    def __init__(self):
        self.mobile_no = ''  # 用户名
        self.password = ''  # 密码
        self.duty_date = ''  # 挂号日期
        self.hospital_id = ''  # 医院ID
        self.department_id = ''  # 科室ID
        self.duty_code = ''  # 1:上午 2:下午
        self.medicare_card_id = ''  # 社保卡号
        self.doctor_name = ''  # 指定专家姓名
        self.system_allocation = True  # 是否服从系统分配

        self.duty = []  # 号源
        self.patient_id = ''  # 就诊人ID
        self.start_time = 0  # 抢号开始时间戳

        # URL
        self.login_url = 'http://www.bjguahao.gov.cn/quicklogin.htm'  # 登录
        self.part_duty_url = 'http://www.bjguahao.gov.cn/dpt/partduty.htm'  # 获取号源信息
        self.send_order_url = 'http://www.bjguahao.gov.cn/v/sendorder.htm'  # 发送短信验证码
        self.confirm_url = 'http://www.bjguahao.gov.cn/order/confirm.htm'  # 挂号
        self.appoint_url = 'http://www.bjguahao.gov.cn/dpt/appoint/{0}-{1}.htm'  # 预约信息页
        self.patient_form_url = 'http://www.bjguahao.gov.cn/order/confirm/{0}-{1}-{2}-{3}.htm'  # 就诊人预约页

        # requests初始化
        self.session = requests.Session()
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
        with open(config_path, 'rb') as f:
            data = json.load(f)
            self.mobile_no = data.get('username')
            self.password = data.get('password')
            self.duty_date = data.get('dutyDate', '')
            self.hospital_id = data.get('hospitalId')
            self.department_id = data.get('departmentId')
            self.duty_code = data.get('dutyCode')
            self.medicare_card_id = data.get('medicareCardId', '')
            self.doctor_name = data.get('doctorName', '')
            self.system_allocation = data.get('SystemAllocation', True)

            logging.info('配置加载完成')
            logging.debug('手机号:' + self.mobile_no)
            logging.debug('挂号日期:' + self.duty_date)
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
        m = re.search(r'<span>预约周期：</span>(?P<appointDay>\d+)<script.*', data)
        appoint_day = m.group('appointDay')
        logging.debug('预约周期: ' + appoint_day)
        today = time.time()
        if self.duty_date == '':
            self.duty_date = time.strftime('%Y-%m-%d', time.localtime(today + int(appoint_day) * 24 * 3600))
        logging.info('挂号日期为: ' + self.duty_date)

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
            logging.error('登录失败', e)
            return False

    def choose_doctor(self):
        """
        选择医生
        :return: dict or None
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
                self.duty = data.get('data')
            if len(self.duty) == 0:  # 还未放号
                return {}
            else:
                for item in self.duty:  # 打印号源列表
                    print(item.get('doctorName'), item.get('skill'), item.get('totalFee'),
                          item.get('remainAvailableNumber'), sep='\t')
                if self.doctor_name:  # 选择指定的医生
                    for doctor in self.duty[::-1]:
                        if doctor.get('doctorName') == self.doctor_name and doctor.get('remainAvailableNumber') > 0:
                            logging.info('选中: ' + doctor.get('doctorName'))
                            return doctor
                    if not self.system_allocation:  # 不服从系统分配
                        return None
                for doctor in self.duty[::-1]:  # 从最好的医生开始选择
                    if doctor.get('remainAvailableNumber') > 0:
                        logging.info('选中: ' + doctor.get('doctorName'))
                        return doctor
            return None  # 号已抢完
        except Exception as e:
            logging.error('选择失败', e)
            return None

    def get_patient_id(self, doctor):
        """
        获取就诊人ID
        :param doctor: dict
        :return: string or None
        """
        url = self.patient_form_url.format(self.hospital_id, self.department_id,
                                           doctor.get('doctorId'), doctor.get('dutySourceId'))
        res = self.request('get', url)
        data = res.text
        m = re.search(r'<input type="radio" name="hzr" value="(?P<patientId>\d+)"[^>]*>', data)
        if m is None:
            logging.error('获取就诊人ID失败')
            return None
        else:
            self.patient_id = m.group('patientId')
            logging.info('就诊人ID: ' + self.patient_id)
            return self.patient_id

    def get_sms_verify_code(self):
        """
        获取短信验证码
        :return: bool
        """
        res = self.request('post', self.send_order_url, data='')
        logging.debug('response: ' + res.text)
        try:
            data = res.json()
            if data.get('code') == 200:
                logging.info('获取验证码成功')
                return True
            else:
                logging.error(data.get('msg'))
                return False
        except Exception as e:
            logging.error('获取短信验证码失败', e)
            return False

    def get_register(self, doctor, sms_code):
        """
        挂号
        :param doctor: dict
        :param sms_code: string
        :return: bool
        """
        args = dict(hospitalId=self.hospital_id,
                    departmentId=self.department_id,
                    doctorId=str(doctor.get('doctorId')),
                    dutySourceId=str(doctor.get('dutySourceId')),
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
            if data.get('code') == 200:
                logging.info('挂号成功')
                return True
            else:
                logging.error(data.get('msg'))
                return False
        except Exception as e:
            logging.error('挂号失败', e)
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
                doctor = self.choose_doctor()
                if doctor:
                    if self.get_patient_id(doctor):
                        if self.get_sms_verify_code():
                            sms_code = input('请输入短信验证码: ')
                            res = self.get_register(doctor, sms_code)
                            if res:
                                break
                    time.sleep(1)
                elif doctor == {}:
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
                        filename='reg.log',
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    reg = Registration()
    reg.run('./config.json')

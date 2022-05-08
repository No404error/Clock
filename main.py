import warnings
import requests
import json
import sys

#json bytes->str
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8');
        return json.JSONEncoder.default(self, obj)

#推送
class pushinfo:
    url='http://www.pushplus.plus/send'
    data = {
        "token":"",
        "title":"SUT打卡",
        "content":"",
        "template":"json"
    }
    def send(self,token,content):
        self.data["token"]=token
        self.data["content"]=content
        body=json.dumps(self.data,cls=MyEncoder).encode(encoding='utf-8')
        headers = {'Content-Type':'application/json'}
        requests.post(self.url,data=body,headers=headers)


class ClockIn:
    def __init__(self):
        self.clear_baseheader()
        self.clear_forminfo()
        self.clear_logininfo()
        self.add_jsessionid()

    def clear_baseheader(self):
        self.base_headers = {
            'Host': 'yqtb.sut.edu.cn',
            'Connection': 'keep-alive',
            'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36',
            'Accept': None,
            'Sec-Fetch-Site': None,
            'Sec-Fetch-Mode': None,
            'Sec-Fetch-Dest': None,
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        }
    def clear_logininfo(self):
        self.login_info = {}
    def clear_forminfo(self):
        self.form_info = {
            'punch_form': {
                'mqszd': None,
                'sfybh': None,
                'mqstzk': None,
                'jcryqk': None,
                'glqk': None,
                'jrcltw': None,
                'sjhm': None,
                'jrlxfs': None,
                'xcsj': None,
                'gldd': None,
                'zddw': None
            },
            'date': None
        }

    def get_user_info(self,account,password):
        if account or password:
            if account and password:
                self.login_info['user_account'] = account
                self.login_info['user_password'] = password
                return
            else:
                raise Exception("The two parameters '--account' and '--password' need to be used together")


    # 获得服务器发给的 jsessionid， 将其加入Cookie中
    def add_jsessionid(self):
        url = 'https://yqtb.sut.edu.cn/login/base'

        # headers 中有些信息不是必须的(有些信息服务器不会检查), 但为了模拟真实使用浏览器打卡避免被查到，把所有header信息补全
        l_headers = self.base_headers.copy()
        l_headers['Upgrade-Insecure-Requests'] = '1'
        l_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
        l_headers['Sec-Fetch-Site'] = 'none'
        l_headers['Sec-Fetch-Mode'] = 'navigate'
        l_headers['Sec-Fetch-User'] = '?1'
        l_headers['Sec-Fetch-Dest'] = 'document'

        try:
            r = requests.get(url=url, headers=l_headers, verify=False)
        except Exception:
            raise Exception('Failed to get jsessionid')
        cookie_info = r.cookies._cookies['yqtb.sut.edu.cn']['/']
        self.base_headers['Cookie'] = 'JSESSIONID={}; nginx={}'.format(cookie_info['JSESSIONID'].value, cookie_info['nginx'].value)

    # 登录
    def login(self):
        url = 'https://yqtb.sut.edu.cn/login'

        self.base_headers['Accept'] = '*/*'
        self.base_headers['Sec-Fetch-Site'] = 'same-origin'
        self.base_headers['Sec-Fetch-Mode'] = 'cors'
        self.base_headers['Sec-Fetch-Dest'] = 'empty'
        self.base_headers['Content-Type'] = 'application/json'
        self.base_headers['X-Requested-With'] = 'XMLHttpRequest'
        self.base_headers['Origin'] = 'https://yqtb.sut.edu.cn'

        l_headers = self.base_headers.copy()
        l_headers['Referer'] = 'https://yqtb.sut.edu.cn/login/base'

        try:
            r = requests.post(url=url, headers=l_headers, json=self.login_info, verify=False)
        except Exception:
            raise Exception('Failed to get login results')

        return r.json()

    # 获得打卡日期json
    def get_homedate(self):
        url = 'https://yqtb.sut.edu.cn/getHomeDate'

        l_headers = self.base_headers.copy()
        l_headers['Content-Length'] = '0'
        l_headers['Referer'] = 'https://yqtb.sut.edu.cn/home'

        try:
            r = requests.post(url=url, headers=l_headers, verify=False)
        except Exception:
            raise Exception('Failed to get homedate form')

        return r.json()

    # 获得前一天的打卡信息
    def get_yesterday_punch_form(self, yesterday_date: str):
        url = 'https://yqtb.sut.edu.cn/getPunchForm'

        l_headers = self.base_headers.copy()
        l_headers['Referer'] = 'https://yqtb.sut.edu.cn/home'

        r = requests.post(url=url, headers=l_headers, json={'date': yesterday_date}, verify=False)
        return r.json()

    # 提交打卡信息
    def push_punch_form(self, now_date: str, yesterday_date: str):
        yesterday_form = self.get_yesterday_punch_form(yesterday_date)
        if yesterday_form['code'] != 200:
            self.failed_reason = f'获取前一天打卡信息失败: {yesterday_form}'
            sys.exit(0)
        url = 'https://yqtb.sut.edu.cn/punchForm'

        l_headers = self.base_headers.copy()
        l_headers['Referer'] = 'https://yqtb.sut.edu.cn/home'

        # 真实的form, punch_form的值为字符串
        true_form = {
            'punch_form': '',
            'date': now_date
        }

        for field in yesterday_form['datas']['fields']:
            val = field['user_set_value']
            if val != 'null':
                self.form_info['punch_form'][field['field_code']] = val
            else:
                self.form_info['punch_form'][field['field_code']] = ''
        true_form['punch_form'] = json.dumps(self.form_info['punch_form'])

        r = requests.post(url=url, headers=l_headers, json=true_form, verify=False)

        return r.json()

    def clock_in(self,account,password):
        self.clear_logininfo()
        self.get_user_info(account,password)
        login_res = self.login()
        if login_res['code'] != 200:
            raise Exception('Failed to login, check your account and password')

        homedate_json = self.get_homedate()
        if homedate_json['code'] != 200:
            raise Exception('Received a bad response when while getting homedate form')

        latest_date_json = homedate_json['datas']['hunch_list'][0]
        yesterday_date_json = homedate_json['datas']['hunch_list'][1]

        if latest_date_json['state'] == 0:
            if yesterday_date_json['state'] == 0:
                raise Exception("Can't get your clock-in information for yesterday")

            push_res = self.push_punch_form(
                latest_date_json['date1'], yesterday_date_json['date1'])
            if push_res['code'] != 200:
                raise Exception("Can't push clock-in form to server")
        else:
            raise Exception("已经打过卡了")


if __name__ == '__main__':
    warnings.filterwarnings('ignore')
    information = open('Inform.txt', 'rb').read().split()
    account_table = []
    password_table = []
    push_token_table = []
    pos = 0
    for i in information:
        strs = str(information[pos], encoding="utf-8")
        if pos % 3 == 0:
            account_table.append(strs)
        elif pos % 3 == 1:
            password_table.append(strs)
        elif pos % 3 == 2:
            push_token_table.append(strs)
        pos += 1
    if not (len(account_table) == len(password_table) and len(account_table) == len(push_token_table)):
        print('information have wrong')
        exit(-1)

    push = pushinfo()
    cl = ClockIn()
    for i in range(0, len(account_table)):
        state = {'打卡状态': '',
                 '身份信息':{
                     'password': password_table[i],
                     'account':account_table[i]
                    },
                 '其他消息':''
                 }
        while True:
            try:
                cl.clock_in(account_table[i], password_table[i])
                state['打卡状态']='成功'
                state['其他消息']=cl.form_info
                push.send(push_token_table[i], state)
            except Exception as err:
                state['打卡状态']='失败'
                state['其他消息']=str(err)
                push.send(push_token_table[i], state)
            finally:
                break;

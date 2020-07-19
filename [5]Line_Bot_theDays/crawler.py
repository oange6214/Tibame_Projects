import requests
import datetime
import pandas as pd
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
import re



class Weather():
    USER_KEY = 'CWB-B9C0BB38-FFE7-4EF2-9FC5-C082E2B8769A'
    DOC_NAME = 'F-C0032-001'

    def __init__(self, city=''):
        self.url = "https://opendata.cwb.gov.tw/api/v1/rest/datastore/" + self.DOC_NAME
        self.city = city
        self.get_data = {}

        self.cities = ['臺北', '新北', '桃園', '臺中', '臺南', '高雄', '基隆', '新竹', '嘉義']
        self.counties = ['苗栗', '彰化', '南投', '雲林', '嘉義', '屏東', '宜蘭', '花蓮', '臺東', '澎湖', '金門', '連江']

    def setData(self, city=''):
        ''' 名詞處理 '''
        if not city == '':
            self.city = city

        if not self.city == '':
            self.city = self.city.replace('台', '臺')
            if self.city in self.cities:
                self.city += '市'
            elif self.city in self.counties:
                self.city += '縣'

            r = requests.get(self.url,
                             params={"Authorization": self.USER_KEY, "format": "JSON", "locationName": self.city})
            result = r.json()

            ''' START 取天氣資料 '''
            self.get_data['Ln'] = result['records']['location'][0]['locationName']
            if result["success"] and result["records"]['location']:
                data = result["records"]['location'][0]
                nt = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
                for t in range(3):
                    if not t:
                        st = nt
                    else:
                        stime = data['weatherElement'][0]['time'][t]['startTime']
                        st = datetime.datetime.strptime(stime, "%Y-%m-%d %H:%M:%S")

                    etime = data['weatherElement'][0]['time'][t]['endTime']
                    et = datetime.datetime.strptime(etime, "%Y-%m-%d %H:%M:%S")

                    # 篩選 時段
                    if st <= nt <= et:
                        for w in data['weatherElement']:
                            self.get_data[w['elementName']] = w['time'][t]['parameter']['parameterName']
                        break
            ''' END 取天氣資料 '''

    def getData(self):
        if len(self.get_data):
            return self.get_data.get('Ln'), self.get_data.get('Wx'), self.get_data.get('MaxT'), self.get_data.get(
                'MinT'), self.get_data.get('CI'), self.get_data.get('PoP')
        return None


class oil():
    def __init__(self):
        pass

    def getData(self):
        try:
            readData = pd.read_html('https://www2.moeaboe.gov.tw/oil102/oil2017/A01/A0108/tablesprices.asp', header=0)[
                0]
        except:
            return None
        # print(readData)
        oil_list = [readData.loc[1].values.tolist(), readData.loc[0].values.tolist()]
        oil_list[0][6] = oil_list[0][6][:10]
        oil_list[1][6] = oil_list[1][6][:10]

        return oil_list


class lotto():
    def __init__(self):
        self.number_list = []

    def find_history(self, type='威力彩', number='109000005'):
        lotto_select = {
            '威力彩': 1,
            '大樂透': 2,
            '今彩539': 5,
            '雙贏彩': 12,
            '3 星彩': 6,
            '4 星彩': 7,
            '38 樂合彩': 4,
            '49 樂合彩': 3,
            '39 樂合彩': 10
        }

        # 請求回應
        url = 'https://www.taiwanlottery.com.tw/lotto/superlotto638/history.aspx'
        r1 = requests.get(url)
        # 分析網站
        html = BeautifulSoup(r1.text, "lxml")
        content_input = html.find_all("input")
        # 擷取 post 用參數
        data = {}
        for c in content_input:
            try:
                if c.attrs['name']:
                    try:
                        if c.attrs['value']:
                            data[c.attrs['name']] = c.attrs['value']
                    except:
                        data[c.attrs['name']] = ''
            except:
                pass

        data['SuperLotto638Control_history1$DropDownList1'] = lotto_select[type]
        data['SuperLotto638Control_history1$txtNO'] = number
        data['SuperLotto638Control_history1$chk'] = 'radNO'

        # 請求回應
        url = 'https://www.taiwanlottery.com.tw/lotto/superlotto638/history.aspx'
        r1 = requests.post(url, data=data)
        # 分析網站
        html = BeautifulSoup(r1.text, "lxml")
        ft_numbers = html.find_all("td", class_='font_black14b_center')
        sd_numbers = html.find("span", id='SuperLotto638Control_history1_dlQuery_SNo7_0')
        # 判斷是否查詢資料
        no_answers = html.find("span", id="SuperLotto638Control_history1_Label1")

        number_list = []
        if no_answers.text == '':
            for num in ft_numbers:
                number_list.append(num.text.strip())
            number_list = number_list[6:]
            number_list.append(sd_numbers.text)

        return number_list

    def result_all(self, type):
        # 請求回應
        url = 'https://www.taiwanlottery.com.tw/result_all.aspx'
        r1 = requests.get(url)
        # 分析網站
        html = BeautifulSoup(r1.text, "lxml")

        tables = html.find_all('table', class_='tableWin')

        lotto_select = ['威力彩', '大樂透', '今彩539', '雙贏彩', '3 星彩', '4 星彩', '38 樂合彩', '49 樂合彩', '39 樂合彩']
        lotto_result_all_list = []
        for i, table in enumerate(tables):
            # if len(table):
            spans = table.find_all('span')
            name = lotto_select[i]
            num_list = []
            lotto_dict = {}
            lotto_dict['遊戲'] = name
            for j, span in enumerate(spans):
                if j == 0:
                    lotto_dict['期別'] = span.text.replace(' ', '')
                elif j == 1:
                    lotto_dict['開獎日期'] = span.text.replace(' ', '')
                elif j == 2:
                    lotto_dict['兌獎日期'] = span.text.replace(' ', '')
                else:
                    num_list.append(span.text.replace(' ', '').replace('\n', ''))

            if len(num_list) > 5:
                if len(num_list) % 2 == 0:
                    lotto_dict['本期中獎號碼'] = num_list[: len(num_list) // 2]
                else:
                    lotto_dict['本期中獎號碼'] = num_list[: len(num_list) // 2 + 1]
            else:
                lotto_dict['本期中獎號碼'] = num_list

            lotto_result_all_list.append(lotto_dict)

        return lotto_result_all_list[type]



class invoice():
    def __init(self):
        pass

    def show(self, m):
        try:
            content = requests.get("http://invoice.etax.nat.gov.tw/invoice.xml")
            tree = ET.fromstring(content.text)
            items = list(tree.iter(tag='item'))
            container = []
            for i in range(m):
                title = items[i][0].text  # 期別
                ptext = re.findall(r"\d+", items[i][2].text)

                container.append((title, ptext))
            return container
        except:
            return None

if __name__ == '__main__':

    ''' 發票 '''
    # inv = invoice()

    # m = 3
    # old = inv.show(m)
    # for i in range(m):
    #     print(old[i][0])
    #     print('特別獎: ', old[i][1][0])
    #     print('特獎: ', old[i][1][1])
    #     print('頭獎: ', ' '.join(old[i][1][2: 5]))
    #     print('增開六獎: ', ' '.join(old[i][1][5:]))

    ''' 樂透 '''
    # lo = lotto()
    # print(lo.find_history('威力彩', 109000032))   # ex: 109000005
    # lotto_dict = lo.result_all(0)
    # print(lotto_dict['本期中獎號碼'])

    ''' 油價 '''
    # o = oil()
    # oil_price = o.getData()
    # print(oil_price[0])

    ''' 天氣 '''
    # cw = Weather('台北')
    # cw.setData()
    # print(cw.getData())
    pass

import wikipedia
wikipedia.set_lang('ja')

import re
import numpy as np
import wikipedia
import bs4.element as bs4elem
from bs4 import BeautifulSoup

# todo handle English+漢字, '-.,' in the name
EXCEPTION = ['A・T・C事務所','Scope co.,ltd.', '4-Legs',  'オア・グローリー神宮前店', 'インダストリアル・ライト&マジック']

# convert unicode to utf-8 if data is unicode
def utf(data):
    if isinstance(data, unicode):
        data = data.encode('utf-8')
    return data

# return true if data include only Katakana and alphabet
def isKatakanaOrEng(data):
    re_katakana = re.compile(r'[\u30A1-\u30F4]+')
    result_kana = re_katakana.fullmatch(data)
    if result_kana is None:
        return False
    re_roman = re.compile(r'^[a-zA-Z]+$') #a-z:小文字、A-Z:大文字
    result_roman = re_roman.fullmatch(data)
    if result_roman is None:
        return False

    # for d in data:
    #     if not ( '゠' <= utf(d) <= 'ヿ' or re.search('\w', utf(d)) ):
    #         return False
    
    return True

class WikiScraper(object):
    def __init__(self):
        self._name = ''
        self._page = ''
        self._bsObj = None
        self._headlines = []
        self._headline_tag = 'h3'
        self._last_key = ''
        self._result = dict()

    # return string of 'key : value \n'
    def __str__(self):
        output = self._name + '\n'
        for k, v in self._result.items():
            output +=  k + ' : ' 
            for staff in set(v):
                output += staff + ',       '
            output += '\n'
        return output

    def load(self, name, lang='ja', pageid=np.nan):
        self.load_wiki(name=name, pageid=pageid, lang=lang)
        if self._bsObj is not None:
            self.get_list_from_headline('.*スタッフ')
            self.get_table('infobox')
            return True, self._result
        else:
            return False, []


    # load html data from wikipedia
    # name: title of wikipage
    # lang: wikipedia language
    # pageid : id of wikipage.
    def load_wiki(self, name, lang='ja', pageid=np.nan):
        wikipedia.set_lang(lang)
        try:
            if np.isnan(pageid):
                self._page = wikipedia.page(name)
            else:
                self._page = wikipedia.page(pageid=int(pageid))
            self.load_html(name, self._page.html())
        except:
            print('Can not open wikipage of '+name+' with lang '+lang)    
    
    # load html
    # name: title of wikipage
    # html: html string
    def load_html(self, name, html):
        self._bsObj = BeautifulSoup(html, "html.parser", from_encoding='utf-8')   
        self._name = name
    
    # find headline
    # name name of headline, e.g. スタッフ
    def find_headline(self, name):
        headers = self._bsObj.find_all(class_='mw-headline')
        self._headlines = []
        for h in headers:
            if re.search(name, h.text):
#                 print 'findheadline------------', h.parentname
                self._headline_tag = h.parent.name
                self._headlines.append(h)

    # cleauup text
    # wrapper function
    # remove brackets, blank, and \n
    def cleanup_text(func):
        def wrapper(self, key, data):
            value = []
            data = data
            data = re.sub('(［|\[).+?(］|\])','', data) #remove brackets
            data = re.sub('(（|\(|\（).+?(）|\）|\))','', data) #remove brackets
            data = data.strip()  #remove \n, and blank from head and tail
            
            #exception
            for e in EXCEPTION:
                if e in data:
                    value.append(e)
                    data = data.replace(e,'')
            
            value = func(key, data, value)
            key = key.strip()
            if key in self._result:
                self._result[key].extend(value)
            else:
                 self._result[key] = value

        return wrapper

    # cleanup value
    # separate line with , / -> and etc. 
    @cleanup_text
    def cleanup_value_list(key, data, value):
        data = re.split('-', data)[0]
        
        data = re.split('[,、/／→\n]', data) #separate multiple staffs    
        for d in data:
            d = d.strip()
            if not isKatakanaOrEng(d): #separate with '・' for ウレロシリーズ
                value.extend(re.split('[・]', d)) #separate multiple staffs    
#             value.extend(re.split('[,、/／→\n]', data)) #separate multiple staffs    
            else:
                value.append(d) # do not separate with '・' for foregin people
#             value.extend(re.split('[,、/・／→\n]', data)) #separate multiple staffs    

        for i, v in enumerate(value): #remove ※
            value[i]  = re.split('※|●', v)[0].strip()
        
        return value

    # cleanup value
    # separate line with , / -> and etc. 
    @cleanup_text
    def cleanup_value_infobox(key, data, value):
        data = re.split('[※|●]', data)[0]
        data = re.split('[,、/→\n]', data) #separate multiple staffs    
        for d in data:
            d = d.strip()
            if not isKatakanaOrEng(d): #separate with '・' for ウレロシリーズ
                value.extend(re.split('[・]', d)) #separate multiple staffs    
            else:
                value.append(d) # do not separate with '・' for foregin people

        return value
    
    # get list data
    def find_list(self, elt, parent=''):
        # recursive process if there are dl or ul
        for e in elt.find_all(['dl', 'ul']):
#             print e.parent.text
            if e.parent is not None:
                temp =  e.parent.text.split('\n')[0]
                if temp:
                    # researve text as parents
                    parent += e.parent.text.split('\n')[0] + ' '
                    self._last_key = parent
#             for s in e.parent.strings:
#                 parent += s.strip() + ' '
#                 self._last_key = parent
# #                 print parent
#                 break            
            self.find_list(e, parent)
            parent = ''
            if e.parent is not None:
                e.parent.decompose()
        
        # get data from each dd, li or dt
        for e in elt.find_all(['dd', 'li', 'dt']):
            data = e.text
            
            if e.name == 'dd':
                # add data if there is data already ref:朝井リョウ・加藤千恵のオールナイトニッポン staff
                if self._result.get(self._last_key) is not None:
                    data = self._result[self._last_key][-1]+ data
                key = self._last_key
                self._last_value = ''

            elif e.name == 'dt':
                # researve data as a parent
                parent = data
                self._last_key = parent
                continue
                
            elif not re.search('[:：-＝\-\=]',data): 
                # if data do not have :, - and etc, i.e. the separator of role and people, save data as a parent
                if parent == '':
                    parent = self._last_key
                key = parent.strip()
                self._last_value = ''

            else:
                #temp for 水曜どうでしょう　& アルピーANN
                if parent != '':
                    # if parents is not empty, set parent as key
                    key = parent
                    if re.search('：',data):
                        #if ':' is in data, split and data[0] is key and others will be data
                        datas = re.split('：', data)
                        key += datas[0]
                        
                        # connect data except for data[0] in case data has multiple ':'
                        data_temp = ''
                        for d in datas[1:]:
                            data_temp += d
                        data = data_temp
                    
                    elif re.search('-',data):
                        # separate data with '-'  and set first one as data, e.g. アルコ&ピースのANN
                        data = re.split('-', data)
                        key = parent
                        data = data[0]
                        
                else:
                    if re.search('[:：-＝\-\=]',data): 
                        # if parent is empty, separate data and set [0] as key and others as data
                        datas = re.split('[:：-＝\-\=]', data)
                        key = datas[0].strip() 
                        
                        data_temp = ''
                        for d in datas[1:]:
                            data_temp += d
                        data = data_temp

                    else :
                        #if parent is empty and no separator, use last key and
                        key = self._last_key
            
            value = self.cleanup_value_list(key, data)

            self._last_key = key
                
    def get_list_from_headline(self, name):
        self.find_headline(name)
        for headline_start in self._headlines:
            finish = False
            # get html between finded headline and next h[1-6]
            for elt in headline_start.parent.nextSiblingGenerator():
                if elt.name is not None and re.match('h[1-6]', elt.name) and elt.name <= self._headline_tag:
                    break

                if hasattr(elt, 'text'):
                    self.find_list(elt)

    def find_tr(self, table):
        rows = table.findAll('tr')
        for row in rows:
            if len(row.findAll('tr')):
                self.find_tr(row) #recursive
            else:
                index = row.find('th')
                if index is not None:
                    key = index.get_text()
                    value = row.find('td')
                    if value is not None:
                        # replace <br> with \n  to get by .text()
                        value_str = re.sub('</*br/*>', '\n', str(value))
                        value = BeautifulSoup(value_str, "html.parser",  from_encoding='utf-8')
        #                    value = value.get_text().split('\n')
                        value = self.cleanup_value_infobox(key, value.get_text())

        #                     self._result[key] = value


    def get_table(self, class_name='infobox'):
        tables = self._bsObj.findAll('table',{'class':class_name})
        for table in tables:
            self.find_tr(table)




if __name__ == "__main__":
    p = None
    # p = wikipedia.page('朝井リョウと加藤千恵のオールナイトニッポン0(ZERO)')
    # p = wikipedia.page('ウレロ☆シリーズ')
    p = wikipedia.page(pageid=2354614) #'勇者ヨシヒコと魔王の城',
    # p = wikipedia.page('怪奇恋愛作戦')
    # p = wikipedia.page('アルコ&ピースのオールナイトニッポンシリーズ')
    # p = wikipedia.page(pageid=129204)
    # p = wikipedia.page('水曜どうでしょう')
    # p = wikipedia.page('おぎやはぎのメガネびいき')
    # p = wikipedia.page('リーガルハイ')
    # p = wikipedia.page('リバースエッジ大川端探偵社')
    # p = wikipedia.page('SPEC〜警視庁公安部公安第五課 未詳事件特別対策係事件簿〜')
    # p = wikipedia.page('勝手にふるえてろ')
    # p = wikipedia.page('ストロベリーナイト(テレビドラマ)')
    # p = wikipedia.page('アイアンマン (映画)')
    # print p.html()
    # print p
      
    wsc = WikiScraper()
    #wsc.load_wiki('朝井リョウと加藤千恵のオールナイトニッポン0(ZERO)', 'ja')
    wsc.load_html(p.title, p.html())
    # wsc.load_wiki('攻殻機動隊', lang='ja', pageid=129204)
    # wsc.get_list_from_headline('.*スタッフ')
    wsc.get_table('infobox')
    # print '-----------------------------'
    print(wsc)
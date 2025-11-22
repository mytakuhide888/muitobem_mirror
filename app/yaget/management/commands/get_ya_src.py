# -*- coding:utf-8 -*-
import time
import sys, codecs

from django.core.management.base import BaseCommand
import os, os.path
import urllib.error
import urllib.request
from datetime import datetime as dt
import time
import re
import lxml.html

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import YaListUrl, YaItemList

# 共通変数
mydwsrc_dir = "/app/yaget/dwsrc"

#sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class Command(BaseCommand):

    help = 'get from ya src.'
    # 本内容は、test_amsrc_1.py のselenium の使い方にある。

    # コマンドライン引数を指定します。(argparseモジュール https://docs.python.org/2.7/library/argparse.html)
    # 今回はblog_idという名前で取得する。（引数は最低でも1個, int型）
    def add_arguments(self, parser):
        parser.add_argument('s_url', nargs='+')

    # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):
        c_options = Options()
        c_options.add_argument('--headless')
        c_options.add_argument('--no-sandbox')
        c_options.add_argument('--disable-gpu')
        c_options.add_argument('--window-size=1280,1024')

        driver = webdriver.Chrome(chrome_options=c_options)

        """
        options = webdriver.ChromeOptions()
        options.binary_location = "./bin/headless-chromium"
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--single-process")

        # 以下はwin環境での結果なのでlinux用に変更のこと
        
        driver = webdriver.Chrome(
            executable_path="./bin/chromedriver",
            chrome_options=options
        )
        """
        """
        driver = webdriver.Chrome(
            executable_path="C:\\Users\\niiya\\Downloads\\chrome-win\\chromedriver.exe",
            chrome_options=options
        )
        """
        # 保存してみる
        if not os.path.exists(mydwsrc_dir):
            os.mkdir(mydwsrc_dir)

        #options.binary_location = "C:\\Users\\niiya\\Downloads\\chrome-win\\chrome.exe"
        #for s_url in args['s_url']:
        #for s_url in options.s_url:
        self.stdout.write('start.')
        for ss_url in options['s_url']:
            self.stdout.write('ss_url:' + ss_url)
            #self.stdout.write(self.style.SUCCESS('my_s_url:' + s_url))
            driver.get(ss_url)
            #driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')

            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src.txt'
            tfpath = mydwsrc_dir + '/' + tfilename
            #f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(driver.page_source)
            #f.write(src_1)
            f.close()

            ### 読み込んだファイルをDBにかく
            obj = YaListUrl(targeturl = ss_url, filename = tfilename)
            obj.save()

            ### XML解析してリスト用のDBへ
            f_read = codecs.open(tfpath, 'r', 'utf-8')
            s = f_read.read()
            dom = lxml.html.fromstring(s)
            a_list = dom.xpath("//div[@class='th']/table/tbody/tr/td")  # <div id="web">の子要素の<li>の子要素の<a>をすべて抽出
            tmpslink = dom.xpath("//link[@rel='canonical']/@href")
            print('tmpslink')
            print(tmpslink[0])
            tmpsname = dom.xpath("//span[@class='seller__name']")
            print('tmpsname')
            print(tmpsname[0].text_content())
            #tmpdivs = dom.xpath("//div[@class='th']/table/tbody/tr/td/a")
            tmpdivs = dom.xpath("//div[@class='th']/table/tbody/tr/td")
            tmpglink = ''
            for i, j in enumerate(tmpdivs):
                tmp_td_obj = list(j)
                #print(i)
                for ii, jj in enumerate(tmp_td_obj):
                    tmpglink = jj.attrib['href']
                    tmpgid = jj.attrib['href'].split("/")[-1]  # gコード
                    tmp_img_obj = list(jj)
                    tmpgsrc = tmp_img_obj[0].attrib['src']
                    tmpgalt = tmp_img_obj[0].attrib['alt']
                    obj, created = YaItemList.objects.update_or_create(
                        bid = tmpsname[0].text_content(),
                        blink = tmpslink[0],
                        gid = tmpgid,
                        glink = tmpglink,
                        g_img_src = tmpgsrc,
                        g_img_alt = tmpgalt,
                    )
                    obj.save()


        self.stdout.write(self.style.SUCCESS('end of ya_get_src Command!'))
"""
f = open('./src_20181108.txt', mode='w')
#f.write(driver.findElement(By.tagName("body")).getText())
element = driver.find_element_by_id("imgTagWrapperId")
subele = element.find_element_by_tag_name("img")
src_1 = subele.get_attribute("src")
src_2 = subele.get_attribute("data-a-dynamic-image")
#element = driver.find_element_by_id("noFlashContent")
#f.write(driver.find_element_by_id("imgTagWrapperId").text)
f.write(driver.page_source)
f.close()

f = open('./src_1.txt', mode='w')
f.write(src_1)
f.close()

f = open('./src_2.txt', mode='w')
f.write(src_2)
f.close()

ele2 = driver.find_element_by_class_name("a-carousel-row-inner")
print(ele2.get_attribute("outerHTML"))
print(ele2.get_attribute("innerHTML"))

ele3 = driver.find_element_by_id("productDescription")
subele3 = ele3.find_element_by_tag_name("p")

print(subele3.text)
f = open('./src_3.txt', mode='w')
f.write(subele3.text)
f.close()

print(element.tag_name)
print(subele.tag_name)
#print(element)
#print(element.text)
#print(subele.text)
"""
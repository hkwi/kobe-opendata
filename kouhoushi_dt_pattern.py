# coding: UTF-8
#
# helper program to extract datetime patterns in
# http://www.city.kobe.lg.jp/information/public/kouhoushi/
#
# python3 kouhoushi_dt_pattern.py | sort | uniq -c | sort -nr
#
from urllib.request import urlopen
import nkf
import re
import lxml.html
import datetime
import logging
import csv, codecs

def proc(url):
	html = urlopen(url).read().decode("CP932")
	doc = lxml.html.document_fromstring(html)
	proc_doc(doc)

def proc_doc(doc):
	for bs in doc.xpath("//p[@id='breadcrumbsList']"):
		for b in bs.xpath(".//a"):
			ym = re.match("(\d+)年(\d+)月", b.text)
			if ym:
				page_year, page_month = map(int, ym.groups())
				break
	
	contents = doc.xpath("//div[@id='contents']")[0]
	h2list = contents.xpath(".//h2")
	
	for h2 in h2list:
		for e in h2.xpath("./following-sibling::*"):
			if e in h2list:
				break
			
			for txt in e.itertext():
				if txt.startswith("日時は"):
					tms = []
					
					DATE = "(?P<month>\d+)月(?P<day>\d+)日"
					WEEKDAY = "(?P<wday>[月火水木金土日])曜(・[祝休]日)?"
					TIME = "(?P<hour>\d+)時((?P<minute>\d+)分)?"
					COUNT = "(?P<count>\d+)回"
					
					txt = re.sub(DATE, "${DATE}", txt)
					txt = re.sub(WEEKDAY, "${WEEKDAY}", txt)
					txt = re.sub(TIME, "${TIME}", txt)
					txt = re.sub(COUNT, "${COUNT}", txt)
					txt = re.sub("・\d+日", "${OPT_DAY}",txt)
					txt = re.sub("～\d+日", "${END_DAY}",txt)
					
					print(txt)

[proc(url.strip()) for url in open("kouhoushi_url.csv")]

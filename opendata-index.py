# coding: UTF-8
import codecs
import sys
import csv
import lxml.html

dout = csv.writer(codecs.open("opendata-index-download.csv","w", encoding="UTF-8"))
pout = csv.writer(codecs.open("opendata-index-publish.csv","w", encoding="UTF-8"))

fields = None
r = lxml.html.parse('http://www.city.kobe.lg.jp/information/opendata/catalogue.html').getroot()
for e in r.xpath("//h2[@id='midashi356']/following-sibling::table//tr"):
	th = ["".join(x.xpath(".//text()")).strip() for x in e.xpath("td")]
	if fields is None:
		names = ["データタイトル", "ライセンス", "タグ", "形式", "データ時点", "担当局室", "所管課"]
		fields = [th.index(key) for key in names]
		
		dout.writerow(names+["URL"])
		pout.writerow(names+["URL"])
	else:
		for url in e.xpath("td[8]//a/@href"):
			dout.writerow([th[i] for i in fields]+[url])
		for url in e.xpath("td[9]//a/@href"):
			pout.writerow([th[i] for i in fields]+[url])


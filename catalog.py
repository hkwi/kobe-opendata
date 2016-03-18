# coding: UTF-8
# 
# http://www.city.kobe.lg.jp/information/opendata/catalogue.html
# をスクレイピングして、一覧登録されているものを csv として抜き出します。
# 
import sys
import csv
import lxml.html
try:
	"".decode("UTF-8")
	u2b = lambda x:x.encode("UTF-8")
	b2u = lambda x:x.decode("UTF-8")
except:
	u2b = b2u = lambda x:x

lmap = lambda f,x:list(map(f,x))
# lxml likes unicode type, csv likes bytes type

dout = csv.writer(open("catalog-download.csv", "w"))
pout = csv.writer(open("catalog-publish.csv", "w"))

fields = None
r = lxml.html.parse('http://www.city.kobe.lg.jp/information/opendata/catalogue.html').getroot()
for e in r.xpath("//h2[@id='midashi356']/following-sibling::table//tr"):
	th = ["".join(x.xpath(".//text()")).strip() for x in e.xpath("td")]
	if fields is None:
		names = ["データタイトル", "ライセンス", "タグ", "形式", "データ時点", "担当局室", "所管課"]
		names = lmap(b2u, names)
		fields = [th.index(key) for key in names]
		
		dout.writerow(lmap(u2b, names+[b2u("URL")]))
		pout.writerow(lmap(u2b, names+[b2u("URL")]))
	else:
		for url in e.xpath("td[8]//a/@href"):
			dout.writerow(lmap(u2b, [th[i] for i in fields]+[url]))
		for url in e.xpath("td[9]//a/@href"):
			pout.writerow(lmap(u2b, [th[i] for i in fields]+[url]))


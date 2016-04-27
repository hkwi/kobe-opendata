# coding: UTF-8
# 
# http://www.city.kobe.lg.jp/information/opendata/catalogue.html
# をスクレイピングして、一覧登録されているものを csv として抜き出します。
# 
from __future__ import print_function
import yaml
import sys
import csv
import lxml.html
# lxml likes unicode type, csv likes bytes type

dout = csv.writer(open("catalog-download.csv", "w", newline=""))
pout = csv.writer(open("catalog-publish.csv", "w", newline=""))

fields = None
r = lxml.html.parse('http://www.city.kobe.lg.jp/information/opendata/catalogue.html').getroot()
for e in r.xpath("//h2[@id='midashi356']/following-sibling::table//tr"):
	th = ["".join(x.xpath(".//text()")).strip() for x in e.xpath("td")]
	names = "データタイトル ライセンス タグ 形式 データ時点 担当局室 所管課".split()
	if fields is None:
		fields = [th.index(key) for key in names]
		
		dout.writerow(names+["URL"])
		pout.writerow(names+["URL"])
	else:
		for url in e.xpath("td[8]//a/@href"):
			dout.writerow([th[i] for i in fields]+[url])
			print(url)
		for url in e.xpath("td[9]//a/@href"):
			pout.writerow([th[i] for i in fields]+[url])

names = None
data = []
for e in r.xpath("//h2[@id='midashi356']/following-sibling::table//tr"):
	if names is None:
		names = ["".join(x.xpath(".//text()")).strip() for x in e.xpath("td")]
		continue
	
	obj = dict()
	es = [x for x in e.xpath("td")]
	for i,name in enumerate(names):
		if name == "ダウンロード":
			e = es[i].find(".//a")
			if e is not None:
				obj["ダウンロード"] = e.get("href")
		elif name == "掲載ページ":
			e = es[i].find(".//a")
			if e is not None:
				obj["掲載ページ"] = e.get("href")
		elif name == "ライセンス":
			if es[i].xpath('.//img[@src="http://www.city.kobe.lg.jp/information/opendata/img/by.png"]'):
				obj["ライセンス"] = "CC-BY"
			elif es[i].xpath('.//img[@src="http://www.city.kobe.lg.jp/information/opendata/img/cc-by-sa.png"]'):
				obj["ライセンス"] = "CC-BY-SA"
			elif es[i].xpath('.//img[@alt="by-nc"]'):
				obj["ライセンス"] = "CC-BY-NC"
			elif "".join(es[i].xpath(".//text()")).strip() == "著作物ではありません":
				obj["ライセンス"] = "CC0"
		else:
			obj[name] = "".join(es[i].xpath(".//text()")).strip()
	
	data.append(obj)

s = yaml.safe_dump_all(data, allow_unicode=True, default_flow_style=False)
with open("catalog.yml", "w") as fp:
	fp.write(s)


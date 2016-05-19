# coding: UTF-8
# 
# http://www.city.kobe.lg.jp/information/opendata/catalogue.html
# をスクレイピングして、一覧登録されているものを jkan dataset として抜き出します。
# 
import sys
import lxml.html
import collections
import yaml

names = '''データタイトル
ライセンス タグ 形式
データ時点 掲載日
ダウンロード 掲載ページ
担当局室 所管課'''.split()
jkan_names = {"データタイトル":"name", "形式":"format"}

resources = []
index = None
r = lxml.html.parse('http://www.city.kobe.lg.jp/information/opendata/catalogue.html').getroot()
for e in r.xpath("//h2[@id='midashi356']/following-sibling::table//tr"):
	th = ["".join(x.xpath(".//text()")).strip() for x in e.xpath("td")]
	if index is None:
		index = [th.index(n) for n in names]
	else:
		base = {}
		urls = e.xpath("td[%d]//a/@href" % (index[names.index("ダウンロード")]+1))
		if urls:
			base["url"] = str(urls[0])
		
		urls = e.xpath("td[%d]//a/@href" % (index[names.index("掲載ページ")]+1))
		if urls:
			if base:
				base["description"] = str(urls[0])
			else:
				base["url"] = str(urls[0])
				base["format"] = "html"
		
		txts = [(n,th[index[names.index(n)]]) for n in names if n not in "ダウンロード 掲載ページ".split()]
		resources.append(dict(list(base.items())+[(jkan_names.get(k,k),v) for k,v in txts if v]))

data = yaml.load(open("jkan_base.yml", encoding="utf-8"))
data["resources"] = resources
with open("jkan_kobe.yml","wb") as fp:
	yaml.dump(data, fp, encoding="utf-8", default_flow_style=False, allow_unicode=True)

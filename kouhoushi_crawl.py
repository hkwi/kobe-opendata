# coding: UTF-8
import re
import os.path
import html
import urllib.request
import lxml.html
import kouhoushi_info
import csv

rss = '''<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{link}</link>
<description>
</description>
</channel>
</rss>'''
rss_item = '''<item>
 <title>{title}</title>
 <link>{link}</link>
 <description></description>
</item>
'''

def fetch(url):
	# Not using lxml.html.parse(), because we want to use (true) CP932 instead of
	# (declared false) Shift_JIS, as some chars like "～" will be differently coded in Unicode.
	txt = urllib.request.urlopen(url).read().decode("CP932")
	return lxml.html.document_fromstring(txt, base_url=url)

def kouhoushi(url, csvout):
	for li in fetch(url).xpath("//div[@id='contents']//a"):
		href = li.get("href", "")
		minfo = re.match("/information/public/kouhoushi/(?P<year>\d{4})/(?P<year2>\d{2})(?P<month>\d{2})/index.html", href)
		if minfo:
			m = minfo.groupdict()
			assert m["year"][2:] == m["year2"]
			kouhoushi_year_month(urllib.parse.urljoin(url, href),
				list(map(int, (m["year"], m["month"]))),
				csvout)

html_escape_dict = lambda o: dict([(k,html.escape(v) if isinstance(v, str) else v) for k,v in o.items()])

def kouhoushi_year_month(url, year_month, csvout):
	doc = fetch(url)
	for li in doc.xpath("//div[@id='contents']//li/a"):
		if li.text is None:
			continue
		href = li.get("href", "")
		if href.endswith(".pdf"):
			continue
		if re.match("info\d{2}(\-\d{2})?.html", os.path.basename(href)):
			csvout.writerow((urllib.parse.urljoin(url, href), li.text))

if __name__=="__main__":
	root = "http://www.city.kobe.lg.jp/information/public/kouhoushi/"
	kouhoushi(root, csv.writer(open("kouhoushi_url.csv", "w", encoding="UTF-8")))
	
	doc = fetch(root)
	baseurl = "http://hkwi.github.io/kobe-opendata"
	dirname = 'refine/kouhoushi'
	rss_basename = "index.xml"
	rss_doc = lxml.etree.fromstring(rss.format(**html_escape_dict(dict(
		url = "{:s}/{:s}/{:s}".format(baseurl, dirname, rss_basename),
		title = doc.xpath("//head/title")[0].text,
		link = root,
		))))
	channel = rss_doc.xpath("//channel")[0]
	
	import glob
	def fkey(f):
		m = re.match("refine/kouhoushi/(\d{4})-(\d{2})/info.*.xml", f)
		if m:
			return (-int(m.group(1)), -int(m.group(2)), f)
	
	files = sorted(glob.glob("refine/kouhoushi/*/info*.xml"), key=fkey)
	
	for f in files:
		if f.find("2015-09") > 0:
			break
		print(f)
		for i in lxml.etree.parse(f).xpath("//item"):
			channel.append(i)
	
	with open("{0}/{1}".format(dirname, rss_basename), "wb") as f:
		lxml.etree.ElementTree(rss_doc).write(
			f,
			encoding="UTF-8",
			pretty_print=True,
			xml_declaration=True
		)

# coding: UTF-8
import re
import os.path
import html
import urllib.request
import lxml.html
import kouhoushi_info

rss = '''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3c.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/" xmlns:html="http://www.w3.org/1999/xhtml">
<channel rdf:about="{url}">
<title>{title}</title>
<link>{link}</link>
<description>
</description>
<items>
 <rdf:Seq>
 </rdf:Seq>
</items>
</channel>
</rdf:RDF>'''
rss_item = '''<item xmlns="{x}" xmlns:rdf="{rdf}" rdf:about="{url}">
 <title>{title}</title>
 <link>{link}</link>
 <description rdf:datatype="rdf:HTML"></description>
</item>
'''

def fetch(url):
	# Not using lxml.html.parse(), because we want to use (true) CP932 instead of
	# (declared false) Shift_JIS, as some chars like "Å`" will be differently coded in Unicode.
	txt = urllib.request.urlopen(url).read().decode("CP932")
	return lxml.html.document_fromstring(txt, base_url=url)

def kouhoushi(url):
	for li in fetch(url).xpath("//div[@id='contents']//a"):
		href = li.get("href", "")
		minfo = re.match("/information/public/kouhoushi/(?P<year>\d{4})/(?P<year2>\d{2})(?P<month>\d{2})/index.html", href)
		if minfo:
			m = minfo.groupdict()
			assert m["year"][2:] == m["year2"]
			kouhoushi_year_month(urllib.parse.urljoin(url, href), list(map(int, (m["year"], m["month"]))))

html_escape_dict = lambda o: dict([(k,html.escape(v) if isinstance(v, str) else v) for k,v in o.items()])

def kouhoushi_year_month(url, year_month):
	doc = fetch(url)
	
	baseurl = "http://hkwi.github.io/kobe-opendata"
	dirname = 'refine/kouhoushi/{:04d}-{:02d}'.format(*year_month)
	rss_basename = "index.xml"
	rss_doc = lxml.etree.fromstring(rss.format(**html_escape_dict(dict(
		url = "{:s}/{:s}/{:s}".format(baseurl, dirname, rss_basename),
		title = doc.xpath("//head/title")[0].text,
		link = url,
		))))
	
	for li in doc.xpath("//div[@id='contents']//li/a"):
		if li.text is None:
			continue
		href = li.get("href", "")
		if href.endswith(".pdf"):
			continue
		if re.match("info\d{2}(\-\d{2})?.html", os.path.basename(href)):
			for injector in kouhoushi_info.proc(urllib.parse.urljoin(url, href), year_month):
				injector(rss_doc)
		else:
			pass
	
	with open("{0}/{1}".format(dirname, rss_basename), "wb") as f:
		lxml.etree.ElementTree(rss_doc).write(
			f,
			encoding="UTF-8",
			pretty_print=True,
			xml_declaration=True
		)

if __name__=="__main__":
	kouhoushi("http://www.city.kobe.lg.jp/information/public/kouhoushi/")

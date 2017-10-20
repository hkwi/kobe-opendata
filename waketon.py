import lxml.html
import json
import re
import urllib.request

write = print

pre = '''@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
'''
xls = '''
<{href}>
 a dcat:Distribution ;
 dcterms:title "{title}" ;
 dcterms:license <{cc}> ;
 dcat:downloadURL <{href}> ;
 dcat:mediaType "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" .
'''
pdf = '''
<{href}>
 a dcat:Distribution ;
 dcterms:title "{title}" ;
 dcterms:license <{cc}> ;
 dcat:downloadURL <{href}> ;
 dcat:mediaType "application/pdf" .
'''

cc = r"^https?://creativecommons.org/licenses/"

write(pre)
fp = urllib.request.urlopen("http://www.city.kobe.lg.jp/life/recycle/waketon/opendeta.html")
r = lxml.html.parse(fp).getroot()
for n in r.xpath('.//h2[@id="midashi20225"]/following-sibling::*'):
	if n.tag == "p":
		for t in n.itertext():
			m = re.match("(【.*?】)", t)
			if m:
				lang = m.group(1)
	elif n.tag == "ul":
		def output(cca, tmpl, with_lang):
			cca_href = cca.get("href")
			if cca_href is None or not re.match(cc, cca_href):
				return
			
			for a in cca.xpath('.//following-sibling::a'):
				href = a.get("href")
				assert href
				a.make_links_absolute()
				title = a.text
				if with_lang:
					title = lang+a.text
				
				write(tmpl.format(
					href=a.get("href"),
					cc=cca_href,
					title=title,
					))
		
		for cca in n.xpath('.//li[@class="doc-xls"]/a'):
			output(cca, xls, True)
		
		for cca in n.xpath('.//li[@class="doc-pdf"]/a'):
			output(cca, pdf, False)

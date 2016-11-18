import re
import lxml.html
import os.path
from urllib.parse import urlparse

url = "http://www.city.kobe.lg.jp/child/school/lunch/kyusyoku/kondate_shiyousyokuhin.html"
r = lxml.html.parse(url).getroot()
r.make_links_absolute()
for href in r.xpath("//a/@href"):
	pc = urlparse(href)
	if pc.path.startswith("/child/school/lunch/kyusyoku") and pc.path.endswith(".pdf"):
		if re.match("^shiyou", os.path.basename(pc.path)):
			continue
		print(href)

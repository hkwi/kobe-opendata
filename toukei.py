from __future__ import print_function
import lxml.html
checks = [
	"http://www.city.kobe.lg.jp/information/data/statistics/toukei/jinkou/suikeijinkou.html",
	"http://www.city.kobe.lg.jp/information/data/statistics/toukei/jinkou/juukijinkou.html",
]
ps = [
	"http://www.city.kobe.lg.jp/information/data/statistics/toukei/jinkou/suikeidata/",
	"http://www.city.kobe.lg.jp/information/data/statistics/toukei/jinkou/juukidata/",
]

for c in checks:
	r = lxml.html.parse(c).getroot()
	r.make_links_absolute(c)
	for e in r.xpath("//a"):
		href = e.get("href")
		if not href:
			continue
		
		for p in ps:
			if href.startswith(p):
				print(href)

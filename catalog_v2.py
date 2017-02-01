# coding: UTF-8
#
# For data.city.kobe.lg.jp release
#
from __future__ import print_function
import yaml
import json
import xml.etree.ElementTree as ET
import csv
import unicodedata
try:
	from urllib import urlopen
except:
	from urllib.request import urlopen

atom_url = "https://data.city.kobe.lg.jp/data/feeds/dataset.atom"
NS = dict(f="http://www.w3.org/2005/Atom")
dataset = []
while atom_url:
	print(atom_url)
	doc = ET.parse(urlopen(atom_url))
	for e in doc.findall(".//f:entry", NS):
		data = urlopen(e.find('f:link[@rel="enclosure"]', NS).get("href")).read()
		ds = json.loads(data.decode("UTF-8"))
		dataset.append(ds)
	
	nx = doc.find('.//f:link[@rel="next"]', NS)
	if nx is None:
		break
	else:
		atom_url = nx.get("href")

s = yaml.safe_dump_all(dataset, allow_unicode=True, default_flow_style=False)
with open("catalog_v2.yml", "w", encoding="UTF-8", newline="") as f:
	f.write(s)

with open("catalog_v2_resources.txt","w") as fp:
	w = csv.writer(fp)
	for ds in dataset:
		for r in ds["resources"]:
			fmt = unicodedata.normalize('NFKC', r["format"])
			if fmt.lower() == "html":
				continue
			if fmt.lower() == "pdf" and r["url"].endswith("/"):
				# They're specifying pdf links under the url.
				continue
			assert fmt.lower() in "csv xls xlsx ppt pptx pdf xml".split(), r["format"]
			w.writerow((r["url"],))

# coding: UTF-8
#
# For data.city.kobe.lg.jp release
#
import yaml
import json
import xml.etree.ElementTree as ET
import sqlalchemy.orm
try:
	from urllib import urlopen
except:
	from urllib.request import urlopen

atom_url = "https://data.city.kobe.lg.jp/data/feeds/dataset.atom"
NS = dict(f="http://www.w3.org/2005/Atom")
dataset = []
for e in ET.parse(urlopen(atom_url)).findall(".//f:entry", NS):
	ds = json.load(urlopen(e.find('f:link[@rel="enclosure"]', NS).get("href")))
	dataset.append(ds)

s = yaml.safe_dump_all(dataset, allow_unicode=True, default_flow_style=False)
with open("catalog_v2.yml", "wb") as f:
	f.write(s)

with open("catalog_v2_resources.txt","w") as w:
	for ds in dataset:
		for r in ds["resources"]:
			if r["format"].lower() == "html":
				continue
			w.write(r["url"]+"\n")

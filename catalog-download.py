import csv
import sys
import os.path
import urllib.request

for p in csv.DictReader(open("catalog-download.csv", encoding="UTF-8")):
	url = p["URL"]
	with open(os.path.join("import/catalog", os.path.basename(url)), "wb") as out:
		for data in urllib.request.urlopen(url):
			out.write(data)

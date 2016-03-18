import csv
import sys
import os.path
try:
	from urllib.request import urlopen
except:
	from urllib import urlopen

# csv likes bytes type

for p in csv.DictReader(open("catalog-download.csv")):
	url = p["URL"]
	with open(os.path.join("import/catalog", os.path.basename(url)), "wb") as out:
		for data in urlopen(url):
			out.write(data)

# coding: UTF-8
import csv
import sys
import codecs
import json
import os
import logging

fname = sys.argv[1]

def feature(row):
	data = {
		"type": "Feature",
		"properties": row,
	}
	
	lat = [row[k] for k in ["lat", "緯度"] if k in row]
	lng = [row[k] for k in ["long", "lng", "経度"] if k in row]
	try:
		data["geometry"] = {
			"type": "Point",
			"coordinates": [float(lng[0]), float(lat[0])]
		}
	except:
		logging.error("conversion error: {0}".format(row))
	
	return data

os.environ["PYTHONIOENCODING"] = "utf-8"
json.dump({
	"type": "FeatureCollection",
	"features": list(map(feature, csv.DictReader(codecs.open(fname, encoding="utf-8-sig")))),
}, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)

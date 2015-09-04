# coding: UTF-8
import csv
import sys
import codecs
import json

fname = sys.argv[1]

def feature(row):
	return {
		"type": "Feature",
		"geometry": {
			"type": "Point",
			"coordinates": [row["経度"], row["緯度"]],
		},
		"properties": row,
	}

json.dump({
	"type": "FeatureCollection",
	"features": list(map(feature, csv.DictReader(codecs.open(fname, encoding="utf-8-sig")))),
}, sys.stdout, indent=2)

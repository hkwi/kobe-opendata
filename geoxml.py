# coding: UTF-8
import xml.etree.ElementTree
import sys
import codecs
import json

fname = sys.argv[1]

def feature(m):
	row = m.attrib
	return {
		"type": "Feature",
		"geometry": {
			"type": "Point",
			"coordinates": [row["lng"], row["lat"]],
		},
		"properties": row,
	}

json.dump({
	"type": "FeatureCollection",
	"features": list(map(feature, xml.etree.ElementTree.parse(fname).iter("marker"))),
}, sys.stdout, indent=2)

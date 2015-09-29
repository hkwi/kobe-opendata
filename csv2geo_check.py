# coding: UTF-8
import yolp as yolplib
import googlemaps
import codecs
import json
import atexit
import sys
import csv
import os

yolpdb_name = "yolp_cache.json"
try:
	yolpdb = json.load(codecs.open(yolpdb_name, encoding="UTF-8"))
except:
	yolpdb = {}

def yolpdb_save():
	json.dump(yolpdb,
		codecs.open(yolpdb_name, "wb", encoding="UTF-8"),
		indent=2, ensure_ascii=False, sort_keys=True)

atexit.register(yolpdb_save)

def yolp(addr):
	if addr not in yolpdb:
		yolpdb[addr] = yolplib.geocoder(addr)
	return yolpdb[addr]


gmapdb_name = "gmap_cache.json"
try:
	gmapdb = json.load(codecs.open(gmapdb_name, encoding="UTF-8"))
except:
	gmapdb = {}

def gmapdb_save():
	json.dump(gmapdb,
		codecs.open(gmapdb_name, "wb", encoding="UTF-8"),
		indent=2, ensure_ascii=False, sort_keys=True)

atexit.register(gmapdb_save)

gmaps = googlemaps.Client(key=os.environ["GOOGLE_API_KEY"])
def gmap(addr):
	if addr not in gmapdb:
		gmapdb[addr] = gmaps.geocode(addr)
	return gmapdb[addr]

if __name__ == "__main__":
	for f in sys.argv[1:]:
		for row in csv.DictReader(codecs.open(f, encoding="UTF-8")):
			lat = [row[k] for k in ["lat", "緯度"] if k in row]
			lng = [row[k] for k in ["long", "lng", "経度"] if k in row]
			try:
				lat = float(lat[0])
				lng = float(lng[0])
			except:
				print("EGEO", row)
				continue
			
			addr = [row[k] for k in ["location", "住所"] if k in row and row[k]]
			zipc = [row[k] for k in ["zipcode", "郵便番号"] if k in row and row[k]]
			
			yolp_err = gmap_err = "ERESOLV"
			if addr:
				yret = yolp(addr[0])
				if yret["ResultInfo"]["Total"] > 0:
					yolp_err = "ERANGE"
					for feature in yret["Feature"]:
						a,b = feature["Geometry"]["BoundingBox"].split()
						x = [float(r) for r in a.split(",")]
						y = [float(r) for r in b.split(",")]
						if x[0] < lng < y[0] and x[1] < lat < y[1]:
							yolp_err = None
				
				gret = gmap(addr[0])
				if len(gret):
					gmap_err = "ERANGE"
					for code in gret:
						vp = code["geometry"]["viewport"]
						if (vp["southwest"]["lat"] < lat < vp["northeast"]["lat"]
								and vp["southwest"]["lng"] < lng < vp["northeast"]["lng"]):
							gmap_err = None
							
							for c in code["address_components"]:
								if "postal_code" in c["types"]:
									if zipc[0].replace("-","") != c["short_name"].replace("-",""):
										print("EPOSTAL", "gmap=", c["short_name"], "doc=", zipc[0], row)
			else:
				yolp_err = gmap_err = "EADDR"
			
			if yolp_err and gmap_err:
				print(f, yolp_err, gmap_err, lat, lng, addr, yret, gret)

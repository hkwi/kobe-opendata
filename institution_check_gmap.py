# coding: UTF-8
import math
import csv
import sys
import codecs
import googlemaps
import time
import os.path

gmaps = googlemaps.Client(key=sys.argv[1])
fname = sys.argv[2]

DEBUG=True

output = csv.writer(codecs.open(os.path.basename(fname).replace(".csv", "_check.csv"), encoding="utf-8-sig", mode="w"))
fields = None
idx_addr = idx_lat = idx_lon = -1
for row in csv.reader(codecs.open(fname, encoding="utf-8-sig")):
	if fields is None:
		fields = row
		idx_addr = fields.index("住所")
		idx_lat = fields.index("緯度")
		idx_lon = fields.index("経度")
		if idx_lat < 0:
			assert idx_lon < 0
		else:
			assert idx_lon >= 0 # if present, both.
		
		if idx_addr >= 0:
			if idx_lat >= 0:
				fields = ["check"] + fields
			else:
				fields = ["check", "緯度", "経度"] + fields
		
		output.writerow(fields)
		continue
	
	if idx_addr >= 0:
		codes = gmaps.geocode(row[idx_addr])
		if DEBUG:
			print(len(codes))
		if idx_lat >= 0:
			# check mode
			try:
				orig_lat = float(row[idx_lat])
				orig_lon = float(row[idx_lon])
			except:
				output.writerow(["緯度経度エラー"] + row)
			else:
				delta = None
				for code in codes:
					dlat = orig_lat - code["geometry"]["location"]["lat"]
					dlon = orig_lon - code["geometry"]["location"]["lng"]
					d = math.sqrt(dlat*dlat + dlon*dlon)
					if delta is None or d < delta:
						delta = d
				
				if delta is None:
					output.writerow(["geocodeエラー"] + row)
				elif delta<0.001:
					output.writerow([""] + row)
				else:
					output.writerow(["delta={:.4f}".format(delta)] + row)
		else:
			# append mode
			dup = False
			if len(codes) > 1:
				dup = True
			for code in codes:
				check = ""
				if dup:
					check = "DUP {addr}".format(addr=code["formatted_address"])
				
				output.writerow([
					check,
					code["geometry"]["location"]["lat"],
					code["geometry"]["location"]["lng"],
					] + row)
			if not codes:
				output.writerow([
					"geocodeエラー",
					"-",
					"-",
					] + row)

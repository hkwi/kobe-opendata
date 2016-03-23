#coding:UTF-8
# USE PYTHON3, because csv module is really badly designed in unicode enabled python2
import csv
import argparse
import datetime
import zipfile
import os.path
import re
import glob
from SPARQLWrapper import SPARQLWrapper,JSON

def write_data(fp, data):
	fields = set()
	for d in data:
		fields.update(d.keys())
	fields = sorted(list(fields))
	w = csv.writer(fp)
	w.writerow(fields)
	for d in data:
		w.writerow(list(map(lambda x:d.get(x,""), fields)))

agency = [
	dict(
		agency_name="神戸市",
		agency_url="http://www.city.kobe.lg.jp/life/access/transport/subway/",
		agency_timezone="Asia/Tokyo",
		agency_lang="ja",
		agency_phone="078-322-5958"
	)
]
routes = [
	dict(
		route_id="seishin",
	 	route_short_name="西神・山手線",
		route_long_name="",
		route_type=1
	),
	dict(
		route_id="kaigan",
		route_short_name="海岸線",
		route_long_name="",
		route_type=1
	)
]
calendar = [
	dict(
		service_id="w",
		monday=1,
		tuesday=1,
		wednesday=1,
		thursday=1,
		friday=1,
		saturday=0,
		sunday=0,
		start_date="20061201"
	),
	dict(
		service_id="h",
		monday=0,
		tuesday=0,
		wednesday=0,
		thursday=0,
		friday=0,
		saturday=1,
		sunday=1,
		start_date="20061201"
	)
]

geo = dict()
sparql = SPARQLWrapper("http://ja.dbpedia.org/sparql")
sparql.setQuery('''
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbpedia-owl: <http://dbpedia.org/ontology/>
PREFIX dbp-ja: <http://ja.dbpedia.org/resource/>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT distinct ?name, ?lat, ?lon WHERE {
  ?s rdfs:label ?name;
  geo:lat ?lat ;
  geo:long ?lon .
  { ?s dbpedia-owl:servingRailwayLine dbp-ja:神戸市営地下鉄西神・山手線 .}
   union
  { ?s dbpedia-owl:servingRailwayLine dbp-ja:神戸市営地下鉄海岸線 .}
}
''')
sparql.setReturnFormat(JSON)
results = sparql.query().convert()
for result in results["results"]["bindings"]:
	m = re.match(r"^(?P<name>.*?)駅?( \(.*\))?$", result["name"]["value"])
	name = m.groupdict()["name"]
	geo[name] = result

# fill temporary unavaliable values
geo["名谷"] = {"lat":{"value":34.679328}, "lon":{"value":135.094211}}
geo["三宮"] = {"lat":{"value":34.694583}, "lon":{"value":135.193753}}
geo["新長田"] = {"lat":{"value":34.6585}, "lon":{"value":135.1459}}
geo["谷上"] = {"lat":{"value":34.761831}, "lon":{"value":135.171344}}

if __name__=="__main__":
	ap = argparse.ArgumentParser()
	ap.add_argument("--dst", default="refine/subway")
	ap.add_argument("--src",
		default="import/www.city.kobe.lg.jp/life/access/transport/subway/img")
	opts = ap.parse_args()
	
	with open(os.path.join(opts.dst, "agency.txt"), mode="w", encoding="UTF-8") as f:
		write_data(f, agency)
	with open(os.path.join(opts.dst, "routes.txt"), mode="w", encoding="UTF-8") as f:
		write_data(f, routes)
	with open(os.path.join(opts.dst, "calendar.txt"), mode="w", encoding="UTF-8") as f:
		# 3 カ月前には公示がでているはず…
		tm = datetime.datetime.now() + datetime.timedelta(days=31*3)
		for d in calendar:
			d["end_date"]=tm.strftime("%Y%m%d")
		write_data(f, calendar)
	
	trips = []
	stations = set()
	route_stops = set()
	for src in glob.glob(os.path.join(opts.src, "*_[h,w]_*.csv")):
		sname = os.path.basename(src)
		m = re.match(r"open_(?P<route>\w+)_(?P<cal>w|h)_(?P<dir>east|west).csv", sname)
		info = m.groupdict()
		
		with open(src, encoding="CP932") as fp:
			for row in csv.reader(fp):
				name = row[0]
				if name[-1] in "発着":
					name = name[:-1]
				
				if name not in ("始発駅","行先駅"):
					stations.add(name)
					route_stops.add((name,info["route"]))
	
	stop_info = {("谷上","seishin"):{ "駅番号":"S01", "駅構内図":""}}
	stop_name_alias = {
		"ハーバー":"ハーバーランド",
		"中央市場":"中央市場前",
		"運動公園":"総合運動公園",
		"駒ケ林":"駒ヶ林",
	}
	with open(os.path.join(opts.src, "open_kobe_subway_add.csv"), encoding="CP932") as fp:
		for row in csv.DictReader(fp):
			name = row["駅名"]
			if name.endswith("駅"):
				name = name[:-1]
			name = stop_name_alias.get(name, name)
			
			stop_info[(
				name,
				{"西神・山手線":"seishin", "海岸線":"kaigan"}[row["線名"]],
			)] = row
	
	stops = []
	for name in stations:
		stops.append(dict(
			stop_id=name,
			stop_name=name,
			stop_lat=geo[name]["lat"]["value"],
			stop_lon=geo[name]["lon"]["value"],
			location_type=1,
			wheelchair_boarding=1,
		))
	
	for name, route in route_stops:
		info = stop_info[(name, route)]
		stops.append(dict(
			stop_id=info["駅番号"],
			stop_code=info["駅番号"],
			stop_name=name,
			stop_lat=geo[name]["lat"]["value"],
			stop_lon=geo[name]["lon"]["value"],
			stop_url=info["駅構内図"],
			location_type=0,
			parent_station=name,
			wheelchair_boarding=1,
		))
	
	with open(os.path.join(opts.dst, "stops.txt"), mode="w", encoding="UTF-8") as f:
		write_data(f, stops)
	
	stop_times = []
	for src in glob.glob(os.path.join(opts.src, "*_[h,w]_*.csv")):
		src_trips = []
		with open(src, encoding="CP932") as fp:
			r = csv.reader(fp)
			starts = next(r)
			ends = next(r)
			for s,e in zip(starts[1:], ends[1:]):
				src_trips.append(dict(
					start=s,
					end=e,
					stops=[]))
			
			for row in r:
				name = row[0]
				if name[-1] in "発着":
					name = name[:-1]
				
				for i,v in enumerate(row[1:]):
					if not v:
						continue
					src_trips[i]["stops"].append(dict(
						name=name,
						value=v))
		
		sname = os.path.basename(src)
		m = re.match(r"open_(?P<route>\w+)_(?P<cal>w|h)_(?P<dir>east|west).csv", sname)
		if m:
			info = m.groupdict()
			for t in src_trips:
				trip_id = "{0}_{1}_{2}_{3}".format(
					t["start"], 
					info["cal"],
					t["stops"][0]["value"].replace(":","_"),
					info["dir"])
				
				trips.append(dict(
					route_id=info["route"],
					service_id=info["cal"],
					trip_id=trip_id,
					trip_headsign=t["end"],
					direction_id={"east":0,"west":1}[info["dir"]],
				))
				
				for stop_no,stop in enumerate(t["stops"]):
					h,m = tuple(map(int, re.match("(\d+):(\d+)", stop["value"]).groups()))
					if h < 3:
						h += 24
					
					stop_times.append(dict(
						trip_id=trip_id,
						arrival_time="%02d:%02d:00" % (h,m),
						departure_time="%02d:%02d:00" % (h,m),
						stop_id=stop_info[(stop["name"],info["route"])]["駅番号"],
						stop_sequence=stop_no,
					))
	
	with open(os.path.join(opts.dst, "trips.txt"), mode="w", encoding="UTF-8") as f:
		write_data(f, trips)
	
	with open(os.path.join(opts.dst, "stop_times.txt"), mode="w", encoding="UTF-8") as f:
		write_data(f, stop_times)
	
	with zipfile.ZipFile(os.path.join(opts.dst, "../subway.zip"), mode="w") as z:
		def write(path):
			z.write(os.path.join(opts.dst, path), path)
		write("agency.txt")
		write("stops.txt")
		write("routes.txt")
		write("trips.txt")
		write("stop_times.txt")
		write("calendar.txt")

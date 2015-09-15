import sys
import os
import json
import codecs
from urllib.request import urlopen
from urllib.parse import urlencode

'''
Get application id from https://e.developer.yahoo.co.jp/dashboard/ and 
set it environment variable YOLP_APP_ID.
'''

def _json_load(url, qs):
	return json.load(codecs.lookup("utf-8").streamreader(urlopen(url+"?"+urlencode(qs))))

def geocoder(address, **kwargs):
	'''
	http://developer.yahoo.co.jp/webapi/map/openlocalplatform/v1/geocoder.html
	'''
	qs = dict(
		appid = kwargs.get("appid", os.environ.get("YOLP_APP_ID")),
		query = address,
		output = "json",
	)
	for k in ["lat","lon","bbox","datum","ac","al","ar","recursive","sort",
			"exclude_prefecture","exclude_seireishi",
			"start","page","results","detail"]:
		if k in kwargs:
			qs[k] = kwargs[k]
	
	return _json_load("http://geo.search.olp.yahooapis.jp/OpenLocalPlatform/V1/geoCoder", qs)

def reverse_geocoder(lat, lon, **kwargs):
	'''
	http://developer.yahoo.co.jp/webapi/map/openlocalplatform/v1/reversegeocoder.html
	'''
	qs = dict (
		appid = kwargs.get("appid", os.environ.get("YOLP_APP_ID")),
		lat = lat,
		lon = lon,
		output = "json",
	)
	for k in ["datum"]:
		if k in kwargs:
			qs[k] = kwargs[k]
	
	return _json_load("http://reverse.search.olp.yahooapis.jp/OpenLocalPlatform/V1/reverseGeoCoder", qs)


if __name__=="__main__":
	os.environ["PYTHONIOENCODING"] = "UTF-8"
	assert os.environ["YOLP_APP_ID"], "YOLP yahoo appid required"
	
	import argparse
	p = argparse.ArgumentParser()
	p.add_argument("-r", "--reverse", action="store_true")
	p.add_argument("args", nargs="+")
	opts = p.parse_args()
	
	if opts.reverse:
		json.dump(reverse_geocoder(*opts.args), sys.stdout, ensure_ascii=False, indent=2)
	else:
		json.dump(geocoder(*opts.args), sys.stdout, ensure_ascii=False, indent=2)

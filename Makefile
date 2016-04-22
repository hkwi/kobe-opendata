SHELL := /bin/bash

all: refine/subway_gtfs.zip
	python catalog.py
	python catalog-download.py
	python catalog_v2.py
	
	mkdir -p import/catalog_v2
	-wget -N -P import/catalog_v2 -i catalog_v2_resources.txt
	
	wget -N -P import -r -np -A 'nobi-*.html' http://www.city.kobe.lg.jp/child/education/program/index_02-1.html
	
	python3 waketon.py > waketon.ttl
	python3 waketon_json.py
	-wget -N -i <(cat waketon.json | jq -r '.["@graph"][]["@id"]')

import:
	$(MAKE) -C import

refine/subway_gtfs.zip:
	python3 subway_gtfs.py


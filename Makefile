SHELL := /bin/bash

all:
	python catalog.py
	python catalog-download.py
	python catalog_v2.py
	
	mkdir -p import/catalog_v2
	-wget -q -N -P import/catalog_v2 -i catalog_v2_resources.txt
	
	python3 waketon.py > waketon.ttl
	python3 waketon_json.py
	-wget -q -N -i <(cat waketon.json | jq -r '.["@graph"][]["@id"]')
	
	-wget -q -N -P import -r -np -A 'nobi-*.html' http://www.city.kobe.lg.jp/child/education/program/index_02-1.html


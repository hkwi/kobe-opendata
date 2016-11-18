SHELL := /bin/bash

all: catalog waketon nobipass kouhoushi toukei

catalog:
	mkdir -p import/catalog
	-wget -q -N -P import/catalog -i <(python3 catalog.py)
	
	python3 catalog_v2.py
	mkdir -p import/catalog_v2
	-wget -q -N -P import/catalog_v2 -i catalog_v2_resources.txt

waketon:
	PYTHONIOENCODING=utf8 python3 waketon.py > waketon.ttl
	python3 waketon_json.py
	-wget -q -N -x -P import -i <(cat waketon.json | jq -r '.["@graph"][]["@id"]')

nobipass:
	-wget -o waketon.log -N -P import -r -np -A 'nobi-*.html' http://www.city.kobe.lg.jp/child/education/program/index_02-1.html

kouhoushi:
	-wget -o kouhoushi.log -N -P import -r -np -A '*.html' http://www.city.kobe.lg.jp/information/public/kouhoushi/

toukei:
	-wget -o toukei.log -N -P import -x -i <(python3 toukei.py)

lunch:
	-wget -o lunch.log -N -P import -x -i <(python3 lunch.py)

clean:
	-rm *.log

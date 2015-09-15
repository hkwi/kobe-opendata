# coding: UTF-8
import csv
import glob
import nkf
import sys
import codecs
import unicodedata
import io
import xml.etree.ElementTree

def is_blank_row(values):
	return sum([1 for v in values if v]) == 0

def normalize(data):
	NBSP = chr(0xa0)
	return unicodedata.normalize("NFKC", data.replace(NBSP, ""))

def process_aed():
	rows = [r for r in xml.etree.ElementTree.parse("import/catalog/aed--_kobe.xml").iter("marker")]
	fields = ["number","name","zipcode","area","location","lat","lng"]
	for row in rows:
		for k in row.attrib.keys():
			if k not in fields:
				fields.append(k)
	outname = "refine/aed.csv"
	if sys.version_info.major < 3:
		out = csv.writer(open(outname, "wb"))
	else:
		out = csv.writer(codecs.open(outname, "wb", encoding="UTF-8"))
	
	fields = list(fields)
	out.writerow(fields)
	for row in rows:
		out.writerow([normalize(row.attrib[f]) for f in fields])

def process_institution():
	institution_rows = []
	institution_fields = None
	for f in glob.glob("import/catalog/institution*.csv"):
		data = normalize(nkf.nkf("-w", open(f, "rb").read()).decode("UTF-8"))
		for hyphen in [b"\xe2\x80\x90", b"\xe2\x88\x92"]:
			data = data.replace(hyphen.decode("UTF-8"), "-")
		
		def fetch_fields(reader):
			for row in reader:
				if len(row) > 1:
					return row
				return None
		
		if sys.version_info.major < 3:
			data = data.encode("UTF-8")
			readers = [csv.reader(io.BytesIO(data)), csv.reader(io.BytesIO(data), dialect="excel-tab")]
		else:
			readers = [csv.reader(io.StringIO(data)), csv.reader(io.StringIO(data), dialect="excel-tab")]
		
		for rd in readers:
			fields = fetch_fields(rd)
			if fields:
				if institution_fields is None:
					institution_fields = fields
				else:
					assert institution_fields == fields
			
				for r in rd:
					r = [x.replace("\r\n", " ").replace("\n"," ").replace("\r"," ").strip() for x in r]
					if not is_blank_row(r):
						institution_rows.append(r)
				break

	ids = [r[0] for r in institution_rows]
	assert len(ids) == len(set(ids))

	outname = "refine/institution.csv"
	if sys.version_info.major < 3:
		out = csv.writer(open(outname, "wb"))
	else:
		out = csv.writer(codecs.open(outname, "wb", encoding="UTF-8"))
	
	out.writerow(institution_fields)
	[out.writerow(r) for r in institution_rows]


if __name__=="__main__":
	process_institution()
	process_aed()

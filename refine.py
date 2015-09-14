# coding: UTF-8
import csv
import glob
import nkf
import codecs
import unicodedata
try:
	from io import StringIO
except:
	from StringIO import StringIO

def is_blank_row(values):
	return sum([1 for v in values if v]) == 0

def process_institution():
	institution_rows = []
	institution_fields = None
	for f in glob.glob("import/catalog/institution*.csv"):
		data = unicodedata.normalize("NFKC", nkf.nkf("-w", open(f, "rb").read()).decode("UTF-8"))
		for hyphen in [b"\xe2\x80\x90", b"\xe2\x88\x92"]:
			data = data.replace(hyphen.decode("UTF-8"), "-")
		
		def fetch_fields(reader):
			for row in reader:
				if len(row) > 1:
					return row
				return None
	
		for rd in [csv.reader(StringIO(data)), csv.reader(StringIO(data), dialect="excel-tab")]:
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

	out = csv.writer(codecs.open("refine/institution.csv", "wb", encoding="UTF-8"))
	out.writerow(institution_fields)
	[out.writerow(r) for r in institution_rows]


if __name__=="__main__":
	process_institution()

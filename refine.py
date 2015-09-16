# coding: UTF-8
import csv
import glob
import nkf
import sys
import codecs
import unicodedata
import zenhan
import io
import xml.etree.ElementTree

def is_blank_row(values):
	return sum([1 for v in values if v]) == 0

def expect_unicode(func):
	def w(data):
		if isinstance(data, bytes):
			return func(data.decode("UTF-8")).encode("UTF-8")
		return func(data)
	return w

@expect_unicode
def normalize(data):
	NBSP = b"\xC2\xA0".decode("UTF-8")
	return unicodedata.normalize("NFKC", zenhan.z2h(zenhan.h2z(data.replace(NBSP, ""))))

def process_csv():
	files = [("sculpture_kobecity_20141128.csv", "sculpture.csv")]
	for fin,fout in files:
		fin = "import/catalog/"+fin
		fout = "refine/"+fout
		if sys.version_info.major < 3:
			input = open(fin)
			output = open(fout, "wb")
		else:
			input = codecs.open(fin, encoding="UTF-8")
			output = codecs.open(fout, "wb", encoding="UTF-8")
		
		output = csv.writer(output)
		for row in csv.reader(input):
			output.writerow(list(map(normalize, row)))

def process_aed():
	rows = [r for r in xml.etree.ElementTree.parse("import/catalog/aed--_kobe.xml").iter("marker")]
	fields = ["number","name","zipcode","area","location","lat","lng"]
	for row in rows:
		for k in sorted(row.attrib.keys()):
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
		def _py2_utf8(u):
			if sys.version_info.major < 3:
				return u.encode("UTF-8")
			return u
		
		out.writerow([normalize(_py2_utf8(row.attrib[f])) for f in fields])

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
	process_csv()

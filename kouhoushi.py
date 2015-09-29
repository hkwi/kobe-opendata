# coding: UTF-8
# http://www.city.kobe.lg.jp/information/public/kouhoushi/
#
# http://www.w3.org/2003/01/geo/
# http://www.georss.org/w3c.html
#
from urllib.request import urlopen
import nkf
import re
import lxml.html
import datetime
import logging
import csv, codecs
import collections
from io import StringIO
from functools import reduce
import pical

JST = datetime.timezone(datetime.timedelta(hours=9), "JST")
WDAY = "月火水木金土日"

class Page(object):
	def __init__(self, doc, url):
		self.doc = doc
		self.url = url
		
		for bs in doc.xpath("//p[@id='breadcrumbsList']"):
			for b in bs.xpath(".//a"):
				ym = re.match("(\d+)年(\d+)月", b.text)
				if ym:
					self.page_year, self.page_month = map(int, ym.groups())
					break

class Partial(object):
	head = None
	children = None
	
	def __str__(self):
		txt = ""
		if self.head and self.head.tail:
			txt += self.head.tail
		for c in self.children:
			txt += lxml.etree.tostring(c, encoding="unicode")
		return txt
	
	def plain_txt(self):
		txt = []
		if self.head.tail:
			txt.append(self.head.tail)
		for c in self.children:
			txt.extend(list(c.itertext()))
			if c.tail:
				txt.append(c.tail)
		return "\n".join(txt)

class H2(Partial):
	def __init__(self, page, h2):
		self.page = page
		self.head = h2
		self.children = []
	
	def blocks(self):
		bs = []
		b = None
		for e in self.children:
			for txt in e.itertext():
				m = re.match("^（(?P<key>([a-z]|\d)+)）", txt)
				if m:
					k = m.groupdict()["key"]
					if not b:
						pass
					elif re.match("\d+", k) and re.match("\d+", b.key):
						pass
					elif re.match("[a-z]+", k) and re.match("[a-z]+", b.key):
						pass
					else:
						b = Block(self, None)
						b.payload = reduce(lambda a,b:a+b, [list(ie.itertext()) for ie in self.children])
						return [b]
					
					b = Block(self, k)
					bs.append(b)
				
				if b:
					b.payload.append(txt)
		
		if bs:
			for com in ("日時は", "料金は", "場所は"):
				check = True
				for b in bs:
					if "\n".join(b.payload).find(com) < 0:
						check = False
						break
				
				if check:
					return bs
		
		b = Block(self, None)
		b.payload = reduce(lambda a,b:a+b, [list(ie.itertext()) for ie in self.children])
		return [b]


class Block(object):
	def __init__(self, h2, key):
		self.h2 = h2
		self.key = key
		self.payload = []
	
	@property
	def url(self):
		if self.key is None:
			return "{0}#{1}".format(self.h2.page.url, self.h2.head.text)
		else:
			return "{0}#{1}#{2}".format(self.h2.page.url, self.h2.head.text, self.key)
	
	def dt(self):
		page_year = self.h2.page.page_year
		page_month = self.h2.page.page_month
		
		dts = []
		for txt in self.payload:
			if not txt.startswith("日時は"):
				continue
			
			dt = None
			
			DATE = "(?P<month>\d+)月(?P<day>\d+)日"
			DATE2 = "(?P<month2>\d+)月(?P<day2>\d+)日"
			WEEKDAY = "(?P<wday>[月火水木金土日])曜(・[祝休]日)?"
			WEEKDAY2 = "(?P<wday2>[月火水木金土日])曜(・[祝休]日)?"
			TIME = "(?P<hour>\d+)時((?P<minute>\d+)分)?"
			TIME2 = "(?P<hour2>\d+)時((?P<minute2>\d+)分)?"
			COUNT = "(?P<count>\d+)回"
			OPT_DAY = "・(?P<day2>\d+)日"
			END_DAY = "～(?P<day2>\d+)日"
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(page_year, int(m["month"]), int(m["day"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）～$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(page_year, int(m["month"]), int(m["day"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"～$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"～"+TIME2+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm1 = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				tm2 = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour2"]), int(m["minute2"]))
				assert WDAY[tm1.weekday()] == m["wday"], txt
				dt = [
					("DTSTART", tm1, {}),
					("DTEND", tm2, {}),
					]
			
			pat = re.match("日時は"+DATE+"～、"+WEEKDAY+TIME+"～。"+COUNT+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [
					("DTSTART", tm, {}),
					("RRULE", "FREQ=WEEKLY;COUNT={0}".format(m["count"]), {}),
					]
			
			pat = re.match("日時は"+DATE+"～、"+WEEKDAY+TIME+"～"+TIME2+"。"+COUNT+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				tme = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour2"]), int(m["minute2"]))
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tme, {}),
					("RRULE", "FREQ=WEEKLY;COUNT={0}".format(m["count"]), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）～"+DATE2+"（"+WEEKDAY2+"）$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(page_year, int(m["month"]), int(m["day"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				tm2 = datetime.date(page_year, int(m["month2"]), int(m["day2"]))
				assert WDAY[tm2.weekday()] == m["wday2"], txt
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2+datetime.timedelta(days=1), {}), # dtend is exclusive
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"～・"+TIME2+"～$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [
					("DTSTART", tm, {}),
					("RRULE", "FREQ=DAILY;BYHOUR={hour2};BYMINUTE={minute2};COUNT=1".format(**m), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+OPT_DAY+"（"+WEEKDAY2+"）"+TIME+"～$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				tm2 = datetime.datetime(page_year, int(m["month"]), int(m["day2"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm2.weekday()] == m["wday2"], txt
				dt = [
					("DTSTART", tm, {}),
					("RRULE", "FREQ=DAILY;BYMONTHDAY={day2};COUNT=1".format(**m), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+OPT_DAY+"（"+WEEKDAY2+"）"+TIME+"～"+TIME2+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				tm2 = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour2"]), int(m["minute2"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2, {}),
					("RRULE", "FREQ=DAILY;BYMONTHDAY={day2};COUNT=1".format(**m), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+END_DAY+"（"+WEEKDAY2+"）$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(page_year, int(m["month"]), int(m["day"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				tm2 = datetime.date(page_year, int(m["month"]), int(m["day2"]))
				assert WDAY[tm2.weekday()] == m["wday2"], txt
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2+datetime.timedelta(days=1), {}), # dtend is exclusive
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"集合", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）まで", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(page_year, int(m["month"]), int(m["day"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [("DTEND", tm+datetime.timedelta(days=1), {})] # dtend is exclusive
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"入港"+OPT_DAY+"（"+WEEKDAY2+"）"+TIME2+"出港", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(page_year, int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				tm2 = datetime.datetime(page_year, int(m["month"]), int(m["day2"]), int(m["hour2"]), int(m["minute2"]))
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2, {}),
					]
			
			if dt:
				dts.append(dt)
			else:
				logging.error(self.url)
				logging.error(txt)
		
		if not dts:
			logging.error("NO_DT {0}".format(self.url))
			return []
		
		return dts[0]

	def loc(self):
		locs = []
		for txt in self.payload:
			if not txt.startswith("場所は"):
				continue
			
			rest = txt[3:].strip()
			if rest.startswith("（"):
				logging.error("location requires hint for {0}".format(self.url))
			else:
				locs.append(txt[3:])
		
		if len(locs) > 1:
			logging.error("location requires hint for {0}".format(self.url))
		elif len(locs) == 1:
			return locs[0]
		
		return None

def proc(url):
	html = urlopen(url).read().decode("CP932")
	doc = lxml.html.document_fromstring(html)
	page = Page(doc, url)
	
	contents = doc.xpath("//div[@id='contents']")[0]
	h2list = contents.xpath(".//h2")
	
	rows = []
	for h2 in h2list:
		item = H2(page, h2)
		rows.append(item)
		
		for e in h2.xpath("./following-sibling::*"):
			if e in h2list:
				break
			
			item.children.append(e)
	
	base = pical.Calendar("VCALENDAR", None)
	try:
		ps = pical.parse(codecs.open("kouhoushi_hint-{:04d}-{:02d}.ics".format(page.page_year, page.page_month), encoding="UTF-8"))
		assert len(ps) == 1
		base = ps[0]
	except:
		pass
	
	output = pical.Calendar("VCALENDAR", base.tzdb)
	output.properties.append(("VERSION", "2.0", {}))
	output.properties.append(("PRODID", "github.com/hkwi/kobe-opendata/kouhoushi", {}))
	for row in rows:
		bs = row.blocks()
		for b in bs:
			evs = [ev for ev in base.children if ev.get("URL").startswith(b.url)]
			if not evs:
				ev = pical.Component.factory("VEVENT", output.tzdb)
				ev.properties.append(("URL", b.url, {}))
				dt = b.dt()
				for name,value,params in dt:
					if name == "RRULE":
						value = pical.Recur.parse(value, output.tzdb)
					ev.properties.append((name,value,params))
				
				loc = b.loc()
				if loc:
					ev.properties.append(("LOCATION", loc, {}))
				
				evs.append(ev)
			
			for ev in evs:
				ev.properties.append(("SUMMARY", b.h2.head.text, {}))
				ev.properties.append(("DESCRIPTION", b.h2.plain_txt(), {}))
			
			for ev in evs:
				output.children.append(ev)
	
	for l in output.serialize():
		print(l)

[proc(url.strip()) for url in open("kouhoushi_url.csv") if url.startswith("http://")]
#proc_doc(lxml.html.document_fromstring(open("info04.html", "rb").read().decode("CP932")))

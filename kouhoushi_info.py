# coding: UTF-8
# 
# kouhoushi_url.csv の URL を読み込んで、解析し、
# refine 以下に RSS と ICS ファイルを出力します。
#
# また同時に、解釈に不足していたヒント情報を
# カレントディレクトリに出力します。
#
from urllib.request import urlopen
from urllib.parse import urlparse
import nkf
import re
import lxml
import lxml.etree
import lxml.html
import lxml.html.clean
import datetime
import logging
import csv, codecs
import collections
from io import StringIO
import pical
import hashlib
import os.path
import html
import itertools
import atexit
import functools
import contextlib

JST = datetime.timezone(datetime.timedelta(hours=9), "JST")
WDAY = "月火水木金土日"

rss = '''<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{link}</link>
<description>
</description>
</channel>
</rss>'''
rss_item = '''<item>
 <title>{title}</title>
 <link>{link}</link>
 <description></description>
</item>
'''

html_escape_dict = lambda o: dict([(k,html.escape(v) if isinstance(v, str) else v) for k,v in o.items()])

class HintRequired(Exception):
	def fill(self, ev):
		for line in self.args:
			p = re.match("(?P<name>[^:;]+)(?P<params>;[^:;]+)?:(?P<value>.*)$", line)
			if not p:
				raise Exception("Hint arg error {0}".format(line))
			
			info = p.groupdict()
			if info["params"]:
				raise Exception("unsupported line:{0}".format(line))
			ev.properties.append((info["name"], info["value"], {}))

class Page(object):
	doc = None # xml document
	url = None # origin
	year_month = ()
	def __init__(self, doc, url, year_month=None):
		self.doc = doc
		self.url = url
		if year_month is None:
			self.year_month = (None, None)
			for bs in doc.xpath("//p[@id='breadcrumbsList']"):
				for b in bs.xpath(".//a"):
					ym = re.match("(\d+)年(\d+)月", b.text)
					if ym:
						self.year_month = tuple(map(int, ym.groups()))
		else:
			self.year_month = year_month

class PartialPage(object):
	'''
	ページのある一部領域を表現する
	'''
	page = None
	head = None
	elements = None
	
	def __init__(self, page, head=None):
		self.page = page
		self.head = head
		self.elements = []
	
	def __str__(self):
		txt = ""
		if self.head and self.head.tail:
			txt += self.head.tail
		for e in self.elements:
			txt += lxml.etree.tostring(e, encoding="unicode")
		return txt
	
	def itertext(self):
		if self.head.tail:
			yield self.head.tail
		
		for e in self.elements:
			for txt in e.itertext():
				yield txt
			
			if e.tail:
				yield e.tail
	
	def plain_txt(self):
		return "\n".join(list(self.itertext()))

BLOCK_METHOD_NONE, BLOCK_METHOD_AUTO, BLOCK_METHOD_FILE = range(3)

class KobeH1(PartialPage):
	@property
	def url(self):
		return "{0}#{1}".format(self.page.url, self.fragment)
	
	@property
	def fragment(self):
		return self.head.text
	
	def blocks(self, hint):
		b = Block(self)
		b.title = self.head.text
		return [b]

class AutoBlock(Exception):
	pass

class KobeH2(PartialPage):
	@property
	def url(self):
		return "{0}#{1}".format(self.page.url, self.fragment)
	
	@property
	def fragment(self):
		return self.head.text
	
	def blocks(self, hint):
		'''
		H2 の情報の中に複数の情報が列挙されているケースがあり、それを分割する。
		分割を自動で判別できる場合が多いが、判別に失敗するケースもあり、それはヒントファイルで補う。
		'''
		block_method = BLOCK_METHOD_NONE
		bs = []
		try:
			for e in self.elements:
				if e.tag != "p":
					raise AutoBlock()
			
			key = None
			is_last = False
			for e in self.elements:
				for txt in e.itertext():
					m = re.match("^（(?P<key>([a-z]|\d)+)）(?P<subtitle>.*)$", txt)
					if m:
						if is_last:
							raise AutoBlock()
						
						info = m.groupdict()
						nk = info["key"]
						if key is None:
							key = nk
						elif re.match("\d+", key) and re.match("\d+", nk):
							key = nk
						elif re.match("[a-z]+", key) and re.match("[a-z]+", nk):
							key = nk
						else:
							raise AutoBlock()
						
						b = Block(self)
						b.key = key
						b.title = self.head.text
						b.subtitle = info["subtitle"]
						b.html = [e]
						bs.append(b)
					else:
						is_last = True
						for b in bs:
							b.html.append(e)
					break
			
			if bs:
				for com in ("日時は", "料金は", "場所は"):
					check = True
					for b in bs:
						txt = itertools.chain(*[e.itertext() for e in b.html])
						if "\n".join(list(txt)).find(com) < 0:
							check = False
							break
					if check:
						block_method = BLOCK_METHOD_AUTO
						break
		except AutoBlock:
			pass
		
		if block_method == BLOCK_METHOD_NONE:
			key2ev = collections.OrderedDict()
			for ev in hints(*self.page.year_month).children:
				url = ev.get("URL")
				if ev.name == "VEVENT" and url and url.startswith(self.url):
					key = None
					if len(url) > len(self.url):
						assert url[len(self.url)] == "#"
						key = url[len(self.url)+1:]
					if key in key2ev:
						key2ev[key].append(ev)
					else:
						key2ev[key] = [ev]
			
			if key2ev:
				block_method = BLOCK_METHOD_FILE
				bs = []
				for key, evs in key2ev.items():
					b = Block(self)
					b.key = key
					b.title = self.head.text
					b.html = self.elements
					b.events = evs
					bs.append(b)
		
		if block_method == BLOCK_METHOD_NONE:
			b = Block(self)
			b.title = self.head.text
			b.html = self.elements
			bs = [b]
		
		if block_method in (BLOCK_METHOD_NONE, BLOCK_METHOD_AUTO):
			for b in bs:
				b.events = []
				for ev in hints(*self.page.year_month).children:
					url = ev.get("URL")
					if ev.name == "VEVENT" and url and url.startswith(b.url):
						b.events.append(ev)
				
				if not b.events:
					ev = pical.Component.factory("VEVENT", hint.tzdb)
					b.events = [ev]
		
		for b in bs:
			for ev in b.events:
				if ev.get("SUMMARY"):
					continue
				
				if b.subtitle:
					ev.properties.append(("SUMMARY", "{:s}（{:s}）{:s}".format(b.title, b.key, b.subtitle), {}))
				else:
					ev.properties.append(("SUMMARY", b.title, {}))
			
			for ev in b.events:
				if ev.get("DESCRIPTION"):
					continue
				ev.properties.append(("DESCRIPTION", b.h2.plain_txt(), {}))
			
			for ev in b.events:
				if ev.get("URL"):
					continue
				ev.properties.append(("URL", b.url, {}))
			
			# DTSTART
			hint_required = None
			dt = []
			try:
				dt = b.dt()
			except HintRequired as e:
				hint_required = e
			
			resolved = 0
			for ev in b.events:
				if ev.get("DTSTART"):
					resolved += 1
					continue
				if hint_required:
					continue
				for name,value,params in dt:
					if name == "RRULE":
						value = pical.Recur.parse(value, hint.tzdb)
					ev.properties.append((name,value,params))
			
			if hint_required and (resolved == 0 or resolved != len(b.events)):
				if not b.events:
					ev = pical.Component.factory("VEVENT", hint.tzdb)
					b.events = [ev]
				
				for ev in b.events:
					hint_required.fill(ev)
			
			# LOCATION
			hint_required = None
			loc = None
			try:
				loc = b.loc()
			except HintRequired as e:
				hint_required = e
			
			resolved = 0
			for ev in b.events:
				if ev.get("LOCATION"):
					resolved += 1
					continue
				if loc:
					ev.properties.append(("LOCATION", loc, {}))
			
			if hint_required and (resolved == 0 or resolved != len(b.events)):
				if not b.events:
					ev = pical.Component.factory("VEVENT", hint.tzdb)
					b.events = [ev]
				
				for ev in b.events:
					hint_required.fill(ev)
		
		return bs


class Block(object):
	key = None
	title = None
	subtitle = None
	calendar = None
	html = None
	
	def __init__(self, h2):
		self.h2 = h2
		self.events = []
		self.html = []
	
	@property
	def url(self):
		if self.key:
			return "{0}#{1}".format(self.h2.url, self.key)
		return self.h2.url
	
	@property
	def fragment(self):
		if self.key:
			return "{0}#{1}".format(self.h2.fragment, self.key)
		return self.h2.fragment
	
	def dt(self):
		page_year, page_month = self.h2.page.year_month
		def year(month):
			if month < page_month-2:
				return page_year+1
			return page_year
		
		dts = []
		for txt in itertools.chain(*[e.itertext() for e in self.html]):
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
			TRAIL = "(?P<trail>（((面接・)?予約制|荒天中止|雨天中止)）)?(。雨天中止)?"
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(year(int(m["month"])), int(m["month"]), int(m["day"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）～$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(year(int(m["month"])), int(m["month"]), int(m["day"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"～"+TRAIL+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"～"+TIME2+TRAIL+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm1 = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				tm2 = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour2"]), int(m["minute2"]))
				if WDAY[tm1.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [
					("DTSTART", tm1, {}),
					("DTEND", tm2, {}),
					]
			
			pat = re.match("日時は"+DATE+"～、"+WEEKDAY+TIME+"～。"+COUNT+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [
					("DTSTART", tm, {}),
					("RRULE", "FREQ=WEEKLY;COUNT={0}".format(m["count"]), {}),
					]
			
			pat = re.match("日時は"+DATE+"～、"+WEEKDAY+TIME+"～"+TIME2+"。"+COUNT+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				tme = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour2"]), int(m["minute2"]))
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tme, {}),
					("RRULE", "FREQ=WEEKLY;COUNT={0}".format(m["count"]), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）～"+DATE2+"（"+WEEKDAY2+"）$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(year(int(m["month"])), int(m["month"]), int(m["day"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				tm2 = datetime.date(year(int(m["month2"])), int(m["month2"]), int(m["day2"]))
				if WDAY[tm2.weekday()] != m["wday2"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday2;{0}".format(txt))
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2+datetime.timedelta(days=1), {}), # dtend is exclusive
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"～・"+TIME2+"～$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				assert WDAY[tm.weekday()] == m["wday"], txt
				dt = [
					("DTSTART", tm, {}),
					("RRULE", "FREQ=DAILY;BYHOUR={hour2};BYMINUTE={minute2};COUNT=1".format(**m), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+OPT_DAY+"（"+WEEKDAY2+"）"+TIME+"～$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				tm2 = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day2"]), int(m["hour"]), int(m["minute"]))
				if WDAY[tm2.weekday()] != m["wday2"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday2;{0}".format(txt))
				dt = [
					("DTSTART", tm, {}),
					("RRULE", "FREQ=DAILY;BYMONTHDAY={day2};COUNT=1".format(**m), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+OPT_DAY+"（"+WEEKDAY2+"）"+TIME+"～"+TIME2+"$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				tm2 = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour2"]), int(m["minute2"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2, {}),
					("RRULE", "FREQ=DAILY;BYMONTHDAY={day2};COUNT=1".format(**m), {}),
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+END_DAY+"（"+WEEKDAY2+"）$", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(year(int(m["month"])), int(m["month"]), int(m["day"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				tm2 = datetime.date(year(int(m["month"])), int(m["month"]), int(m["day2"]))
				if WDAY[tm2.weekday()] != m["wday2"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday2;{0}".format(txt))
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2+datetime.timedelta(days=1), {}), # dtend is exclusive
					]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"集合", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [("DTSTART", tm, {})]
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）まで", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.date(year(int(m["month"])), int(m["month"]), int(m["day"]))
				if WDAY[tm.weekday()] != m["wday"]:
					raise HintRequired("X-HINT-REQ-DTSTART:wday;{0}".format(txt))
				dt = [("DTEND", tm+datetime.timedelta(days=1), {})] # dtend is exclusive
			
			pat = re.match("日時は"+DATE+"（"+WEEKDAY+"）"+TIME+"入港"+OPT_DAY+"（"+WEEKDAY2+"）"+TIME2+"出港", txt)
			if not dt and pat:
				m = pat.groupdict("0")
				tm = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["minute"]))
				tm2 = datetime.datetime(year(int(m["month"])), int(m["month"]), int(m["day2"]), int(m["hour2"]), int(m["minute2"]))
				dt = [
					("DTSTART", tm, {}),
					("DTEND", tm2, {}),
					]
			
			if dt:
				dts.append(dt)
			else:
				raise HintRequired("X-HINT-REQ-DTSTART:{0}".format(txt))
		
		if not dts:
			raise HintRequired("X-HINT-REQ-DTSTART:NONE")
		
		return dts[0]

	def loc(self):
		locs = []
		for txt in itertools.chain(*[e.itertext() for e in self.html]):
			if not txt.startswith("場所は"):
				continue
			
			rest = txt[3:].strip()
			if rest.startswith("（"):
				raise HintRequired("X-HINT-REQ-LOCATION:{0}".format(txt))
			else:
				locs.append(txt[3:])
		
		if len(locs) > 1:
			raise HintRequired("X-HINT-REQ-LOCATION:{0}".format(repr(locs)))
		elif len(locs) == 1:
			return locs[0]
		
		return None


_hints = {}
def hints(year, month):
	filename = "kouhoushi_hint-{:04d}-{:02d}.ics".format(year, month)
	if filename in _hints:
		return _hints[filename]
	
	try:
		txt = open(filename, "rb").read().decode("UTF-8")
	except:
		return pical.Calendar("VCALENDAR", None)
	
	try:
		ps = pical.parse(StringIO(txt))
	except Exception as e:
		raise Exception("filename=%s, %s" % (filename, e))
	
	assert len(ps) == 1
	ret = ps[0]
	_hints[filename] = ret
	return ret


_hint_writers = dict()

@contextlib.contextmanager
def hint_writer(filename):
	if filename not in _hint_writers:
		f = open(filename, "w")
		_hint_writers[filename] = f
		f.write("BEGIN:VCALENDAR\r\n")
		def close():
			f.write("END:VCALENDAR\r\n")
			f.close()
		atexit.register(close)
	yield _hint_writers[filename]

def proc(url, year_month=None):
	rss_injectors = []
	
	html_txt = urlopen(url).read().decode("CP932")
	html_txt = lxml.html.clean.Cleaner(javascript=True, frames=True, page_structure=False).clean_html(html_txt)
	doc = lxml.html.document_fromstring(html_txt, base_url=url)
	
	page = Page(doc, url, year_month)
	
	contents = doc.xpath("//div[@id='contents']")[0]
	h1list = contents.xpath(".//h1")
	h2list = contents.xpath(".//h2")
	
	rows = []
	if re.search("\d{2}-\d{2}", os.path.basename(url)):
		for h1 in h1list:
			item = KobeH1(page, h1)
			rows.append(item)
			item.elements = h1.xpath("./following-sibling::*")
	else:
		for h2 in h2list:
			item = KobeH2(page, h2)
			rows.append(item)
			
			for e in h2.xpath("./following-sibling::*"):
				if e in h2list:
					break
				
				item.elements.append(e)
	
	baseurl = "http://hkwi.github.io/kobe-opendata"
	dirname = 'refine/kouhoushi/{:04d}-{:02d}'.format(*page.year_month)
	
	os.makedirs(dirname, exist_ok=True)
	rss_basename = re.sub(".html$", ".xml", os.path.basename(urlparse(url).path))
	rss_doc = lxml.etree.fromstring(rss.format(**html_escape_dict(dict(
		url = "{:s}/{:s}/{:s}".format(baseurl, dirname, rss_basename),
		title = doc.xpath("//head/title")[0].text,
		link = url,
		))))
	
	ics_seq = 0
	
	base = hints(*page.year_month)
	for row in rows:
		for b in row.blocks(base):
			enable_vevent = False
			for ev in b.events:
				if ev.get("DTSTART"):
					enable_vevent = True
			
			ics_basename = None
			if enable_vevent:
				ics_basename = rss_basename.replace(".xml", "-{:d}.ics".format(ics_seq))
				ics_seq += 1
				
				output = pical.Calendar("VCALENDAR", base.tzdb)
				output.properties.append(("VERSION", "2.0", {}))
				output.properties.append(("PRODID", "github.com/hkwi/kobe-opendata/kouhoushi", {}))
				for ev in b.events:
					output.children.append(ev)
				
				with open("{0}/{1}".format(dirname, ics_basename), "wb") as ics:
					for l in output.serialize():
						ics.write(l.encode("UTF-8"))
						ics.write("\r\n".encode("UTF-8"))
			
			def inject_block(b, enable_vevent, rss_doc):
				# emit rss item
				title = b.title
				if b.subtitle:
					title = "{:s}（{:s}）{:s}".format(b.title, b.key, b.subtitle)
			
				parent = rss_doc.xpath(".//channel")[0]
				rss_item_xml = rss_item.format(**html_escape_dict(dict(
					url="{0}/{1}/{2}#{3}".format(baseurl, dirname, rss_basename, b.fragment),
					link=b.url,
					title=title,
					)))
				try:
					rss_item_doc = lxml.etree.fromstring(rss_item_xml)
					rss_item_doc.tail = "\n"
				except:
					print(rss_item_xml)
					raise
			
				parent.append(rss_item_doc)
			
				parent = rss_item_doc.xpath(".//description")[0]
				if b.html:
					c = "".join([lxml.html.tostring(e, encoding="unicode") for e in b.html])
					parent.text = lxml.etree.CDATA(c)
				else:
					c = "".join([lxml.html.tostring(e, encoding="unicode") for e in b.h2.elements])
					parent.text = lxml.etree.CDATA(c)
			
				if enable_vevent:
					e = lxml.etree.fromstring('<enclosure url="{0}/{1}/{2}" type="text/calendar"/>'.format(
						baseurl,
						dirname,
						ics_basename))
					if parent.tail is None:
						parent.tail = ""
					parent.tail += " "
					e.tail = "\n"
					rss_item_doc.append(e)
			
			inject_block(b, enable_vevent, rss_doc)
			rss_injectors.append(functools.partial(inject_block, b, enable_vevent))
			
			for ev in b.events:
				req = False
				for prop in ev.properties:
					if prop[0] == "X-HINT-REQ-DTSTART" and prop[1]=="NONE":
						continue
					if prop[0].startswith("X-HINT-REQ-"):
						req = True
				if req:
					with hint_writer("kouhoushi_req-{:04d}-{:02d}.ics".format(*page.year_month)) as f:
						for l in ev.serialize():
							if l.startswith("BEGIN:"):
								f.write(l)
								f.write("\r\n")
							elif l.startswith("END:"):
								f.write(l)
								f.write("\r\n")
							elif l.startswith("URL:"):
								f.write(l)
								f.write("\r\n")
							elif l.startswith("X-HINT-REQ-"):
								f.write(l.replace("X-HINT-REQ-","X-HINT-"))
								f.write("\r\n")
	
	with open("{0}/{1}".format(dirname, rss_basename), "wb") as f:
		lxml.etree.ElementTree(rss_doc).write(
			f,
			encoding="UTF-8",
			pretty_print=True,
			xml_declaration=True
		)
	
	return rss_injectors

if __name__ == "__main__":
	[proc(url.strip()) for url in open("kouhoushi_url.csv") if url.startswith("http://")]
#proc_doc(lxml.html.document_fromstring(open("info04.html", "rb").read().decode("CP932")))

# coding: UTF-8
import rdflib.store
from rdflib import Graph

# To generate stable ordered json output, in addition to this store,
# you must hack rdflib json_ld use OrderedDict instead of {}.
class Naive(rdflib.store.Store):
	formula_aware = True
	def __init__(self, *args, **kwargs):
		super(Naive, self).__init__(*args, **kwargs)
		self.ns = []
		self.ts = []
	
	def bind(self, prefix, namespace):
		assert ":" not in prefix
		ns = [n for n in self.ns if n[0] != namespace and n[1] != prefix]
		ns.append((namespace, prefix))
		self.ns = sorted(ns, reverse=True)
	
	def _to_iri(self, t):
		for n in self.ns:
			p = n[1]+":"
			if t.startswith(p):
				return "<%s:%s>" % (n[0], t[len(p):])
		return t
	
	def _from_iri(self, t):
		for n in self.ns:
			p = "<"+n[0]
			if t.startswith(p):
				assert t[-1] == ">"
				return n[1]+":"+t[len(p):-1]
		return t
	
	def add(self, triple, *args, **kwargs):
		triple = tuple(map(self._to_iri, triple))
		if triple not in self.ts:
			self.ts.append(triple)
		super(Naive, self).add(triple, *args, **kwargs)
		print(triple)
	
	def remove(self, triple, *args, **kwargs):
		triple = tuple(map(self._to_iri, triple))
		self.ts.remove(triple)
		super(Naive, self).remove(triple, *args, **kwargs)
	
	def triples(self, triple, context=None):
		(s, p, o) = triple
		for triple in self.ts:
			if s is not None and s!=triple[0]:
				continue
			if p is not None and p!=triple[1]:
				continue
			if o is not None and o!=triple[2]:
				continue
			yield triple, [None]

ctx = {
	"@vocab": "http://purl.org/dc/terms/",
	"dcat": {
		"@id": "http://www.w3.org/ns/dcat#",
		"@type": "@id",
	},
}

g = Graph(store=Naive())
g.load("waketon.ttl", format="turtle")
with open("waketon.json","wb") as fp:
	fp.write(g.serialize(format="json-ld", context=ctx, sort_keys=True))

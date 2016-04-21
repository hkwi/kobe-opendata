from rdflib import Graph

ctx = {
	"@vocab": "http://purl.org/dc/terms/",
	"dcat": {
		"@id": "http://www.w3.org/ns/dcat#",
		"@type": "@id",
	},
}

g = Graph()
g.load("waketon.ttl", format="turtle")
with open("waketon.json","wb") as fp:
	fp.write(g.serialize(format="json-ld", context=ctx))

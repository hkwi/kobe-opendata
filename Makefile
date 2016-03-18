all:
	$(MAKE) -C import
	python catalog.py
	python catalog-download.py

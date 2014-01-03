all:

.PHONY: docs
docs:
	PYTHONPATH=$(PWD) $(MAKE) -C docs html
	firefox docs/_build/html/index.html

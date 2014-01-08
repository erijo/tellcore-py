all:

.PHONY: docs
docs:
	PYTHONPATH=$(PWD) $(MAKE) -C docs html
	firefox docs/_build/html/index.html

.PHONY: tests
tests:
	python2 ./run_tests
	python3 ./run_tests
	pypy ./run_tests
	flake8 tellcore
	flake8 bin
#       Ignore "from tellcore.constants import *"
	flake8 --ignore=F403 tests

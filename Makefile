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
#       Ignore F403: "from tellcore.constants import *"
#       Ignore F405: "X may be undefined, or defined from star imports"
#       Ignore E731: "do not assign a lambda expression, use a def"
	flake8 --ignore=F403,F405,E731 tests

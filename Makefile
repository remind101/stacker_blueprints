test:
	flake8 stacker_blueprints
	python setup.py test

move-results:
	./bin/move-results.sh

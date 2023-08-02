help:
	@echo "make help|tests|"


tests:
	py.test -vvs tests


build:
	GITHUB_DUMP='\
    {\
       "ref": "refs/heads/$(shell git branch --show-current)", \
       "sha": "$(shell git rev-parse HEAD)", \
       "run_number": 123, \
       "run_id": 456 \
    }\
    ' python -m build

clean:
	-git checkout src/setuptools_github/__init__.py
	rm -rf dist setuptools_github.egg-info

.PHONY: tests

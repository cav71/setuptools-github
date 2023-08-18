# REF:
#   master  : refs/heads/master"
#   beta    : refs/heads/beta/0.3.7
#   release : refs/tags/release/0.3.7

REF=$(shell git rev-parse --symbolic-full-name HEAD)
SHA=$(shell git rev-parse HEAD)
RUNNO=123
RUNID=5753082134

GITHUB_DUMP="{\"ref\": $(REF), \"sha\": $(SHA), \"run_id\": $(RUNID), \"run_number\": $(RUNNO)}"
export GITHUB_DUMP


help:
	@echo "make help|tests|build"
	@echo ""
	@echo "Vars"
	@echo "  REF:          $(REF)"
	@echo "  SHA:          $(SHA)"
	@echo "  RUNID:        $(RUNID)"
	@echo "  RUNNO:        $(RUNNO)"
	@echo "  GITHUB_DUMP:  $(GITHUB_DUMP)"


tests:
	py.test -vvs tests


.PHONY: build
build:
	rm -rf dist 
	git checkout src/setuptools_github/__init__.py
	GITHUB_DUMP='\
    {\
       "ref": "$(REF)", \
       "sha": "$(SHA)", \
       "run_number": $(RUNNO), \
       "run_id": $(RUNID) \
    }\
    ' python -m build $(NFLAG)


branch:
	rm -rf dist src/setuptools_github/_build.py
	git checkout src/setuptools_github/__init__.py
	GITHUB_DUMP='\
    {\
       "ref": "refs/heads/$(shell git branch --show-current)", \
       "sha": "$(shell git rev-parse HEAD)", \
       "run_number": 92, \
       "run_id": 5767031699 \
    }\
    ' python -m build

clean:
	-git checkout src/setuptools_github/__init__.py README.md
	rm -rf dist setuptools_github.egg-info src/setuptools_github/build.json

.PHONY: tests branch

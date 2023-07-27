help:
	@echo "make help|tests|"


tests:
	PYTHONPATH=src py.test -vvs tests


.PHONY: tests

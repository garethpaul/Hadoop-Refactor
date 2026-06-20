.PHONY: build check lint test

override ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

lint test build: check

check:
	@python3 "$(ROOT)/scripts/check-baseline.py"
	@python3 "$(ROOT)/scripts/test-lzop-hostile-streams.py"
	@python3 "$(ROOT)/scripts/test-lzop-hostile-mutations.py"

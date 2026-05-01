.PHONY: test test-fast

# Run full test suite
test:
	pytest tests/ -v

# Stop on first failure (useful during development)
test-fast:
	pytest tests/ -v -x

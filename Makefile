.PHONY: install lint test test-integration test-mac

install:
	cd server && pip install -e ".[test]"

lint:
	cd server && ruff check src/ tests/
	cd server && mypy src/mcp_kb/

test:
	cd server && pytest tests/ -m "not integration" -v

test-integration:
	cd server && pytest tests/ -m integration -v

test-mac: lint test test-integration

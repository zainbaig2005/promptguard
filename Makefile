PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

dev: install

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy promptguard

test:
	pytest

coverage:
	pytest --cov=promptguard --cov-report=term-missing

validate: lint typecheck test

seed:
	promptguard seed-demo

demo: install seed
	@echo "Start the dashboard with: streamlit run promptguard/dashboard/app.py"

dashboard:
	streamlit run promptguard/dashboard/app.py

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage reports promptguard.db

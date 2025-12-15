.PHONY: setup format lint test tox clean build all

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements.dev.txt
	echo "PYTHONPATH=.venv/lib" > .env
	@echo "Setup complete! Activate with: source .venv/bin/activate"

format:
	.venv/bin/black src tests
	.venv/bin/isort src tests

lint:
	.venv/bin/black --check src tests
	.venv/bin/flake8 src tests
	.venv/bin/pyright src
	.venv/bin/isort --check-only src tests

test:
	.venv/bin/pytest

test-cov:
	.venv/bin/pytest --cov=src/custom_components/vivosun_thermo --cov-report=html:coverage --cov-report=term-missing

tox:
	.venv/bin/tox

clean:
	rm -rf dist/ build/ *.egg-info coverage/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true

build: clean
	.venv/bin/python -m build

all: setup format lint test tox

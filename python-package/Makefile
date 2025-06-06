# Inspired by https://github.com/posit-dev/chatlas/blob/main/Makefile

.PHONY: setup
setup:  ## [py] Setup python environment
	uv sync --all-extras

.PHONY: build
build:   ## [py] Build python package
	@echo "🧳 Building python package"
	@[ -d dist ] && rm -r dist || true
	uv build

.PHONY: publish
publish:
	hatch publish

.PHONY: check
check: check-format check-types ## [py] Run python checks

.PHONY: check-types
check-types:  ## [py] Run python type checks
	@echo ""
	@echo "📝 Checking types with pyright"
	uv run --with pyright pyright

.PHONY: check-format
check-format:
	@echo ""
	@echo "📐 Checking format with ruff"
	uv run --with ruff ruff check src/querychat --config pyproject.toml

.PHONY: format
format: ## [py] Format python code
	uv run --with ruff ruff check --fix src/querychat --config pyproject.toml
	uv run --with ruff ruff format src/querychat --config pyproject.toml

.PHONY: check-tox
check-tox:  ## [py] Run python 3.9 - 3.12 checks with tox
	@echo ""
	@echo "🔄 Running tests and type checking with tox for Python 3.9--3.12"
	uv run tox run-parallel

.PHONY: help
help:  ## Show help messages for make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; { \
		printf "\033[32m%-18s\033[0m", $$1; \
		if ($$2 ~ /^\[docs\]/) { \
			printf "\033[34m[docs]\033[0m%s\n", substr($$2, 7); \
		} else if ($$2 ~ /^\[py\]/) { \
			printf "  \033[33m[py]\033[0m%s\n", substr($$2, 5); \
		} else if ($$2 ~ /^\[r\]/) { \
			printf "   \033[31m[r]\033[0m%s\n", substr($$2, 4); \
		} else { \
			printf "       %s\n", $$2; \
		} \
	}'

.DEFAULT_GOAL := help

# Inspired by https://github.com/posit-dev/shinychat/blob/main/Makefile

# Use qvm to manage quarto
QUARTO_VERSION ?= 1.7.31
QUARTO_PATH = ~/.local/share/qvm/versions/v${QUARTO_VERSION}/bin/quarto
PATH_PKG_R := pkg-r
PATH_PKG_PY := pkg-py
PATH_PKG_JS := js

.PHONY: install-quarto
install-quarto:
	@echo "🔵 Installing quarto"
	@if ! [ -z $(command -v qvm)]; then \
		@echo "Error: qvm is not installed. Please visit https://github.com/dpastoor/qvm/releases/ to install it." >&2 \
		exit 1; \
	fi
	qvm install v${QUARTO_VERSION}
	@echo "🔹 Updating .vscode/settings.json"
	@awk -v path="${QUARTO_PATH}" '/"quarto.path":/ {gsub(/"quarto.path": ".*"/, "\"quarto.path\": \"" path "\"")} 1' .vscode/settings.json > .vscode/settings.json.tmp && mv .vscode/settings.json.tmp .vscode/settings.json
	@echo "🔹 Updating .github/workflows/quartodoc.yaml"
	@awk -v ver="${QUARTO_VERSION}" '/QUARTO_VERSION:/ {gsub(/QUARTO_VERSION: .*/, "QUARTO_VERSION: " ver)} 1' .github/workflows/quartodoc.yaml > .github/workflows/quartodoc.yaml.tmp && mv .github/workflows/quartodoc.yaml.tmp .github/workflows/quartodoc.yaml

.PHONY: docs
docs: r-docs py-docs-render ## [docs] Build the documentation

# .PHONY: docs-preview
# docs-preview:  ## [docs] Preview the documentation
# 	@npx http-server docs -p 8080

# .PHONY: js-setup
# js-setup:  ## [js] Install JS dependencies
# 	@echo "🆙 Setup JS dependencies"
# 	cd $(PATH_PKG_JS) && npm install

# .PHONY: js-setup-ci
# js-setup-ci:  ## [js] Install JS dependencies as CI
# 	@echo "🆙 Setup JS dependencies"
# 	cd $(PATH_PKG_JS) && npm ci

# .PHONY: js-lint
# js-lint:  ## [js] Lint JS code
# 	@echo "📐 Linting JS code"
# 	cd $(PATH_PKG_JS) && npm run lint

# .PHONY: js-build
# js-build:  ## [js] Build JS code
# 	@echo "🧳 Building JS code"
# 	cd $(PATH_PKG_JS) && npm run build

# .PHONY: js-build-watch
# js-build-watch:  ## [js] Build JS code in watch mode
# 	@echo "🧳 Building JS code in watch mode"
# 	cd $(PATH_PKG_JS) && npm run watch

.PHONY: r-setup
r-setup:  ## [r] Install R dependencies
	@echo "🆙 Updating R dependencies"
	cd $(PATH_PKG_R) && Rscript -e "pak::local_install_dev_deps()"

.PHONY: r-check
r-check: r-check-format r-check-tests r-check-package  ## [r] All R checks

.PHONY: r-document
r-document: ## [r] Document package
	@echo "📜 Documenting R package"
	cd $(PATH_PKG_R) && Rscript -e "devtools::document()"

.PHONY: r-format
r-format:  ## [r] Format R code
	air format $(PATH_PKG_R)/

.PHONY: r-check-package
r-check-package:  ## [r] Check package
	@echo ""
	@echo "🔄 Running R CMD Check"
	cd $(PATH_PKG_R) && Rscript -e "devtools::check(document = FALSE)"

.PHONY: r-check-tests
r-check-tests:  ## [r] Check tests
	@echo ""
	@echo "🧪 Running R tests"
	cd $(PATH_PKG_R) && Rscript -e "devtools::test(reporter = 'check')"

.PHONY: r-check-format
r-check-format:  ## [r] Check format
	@echo ""
	@echo "📐 Checking R format"
	air format --check $(PATH_PKG_R)/

# .PHONY: r-update-dist
# r-update-dist: ## [r] Update shinychat web assets
# 	@echo ""
# 	@echo "🔄 Updating shinychat web assets"
# 	if [ -d $(PATH_PKG_R)/inst/lib/shiny ]; then \
# 		rm -rf $(PATH_PKG_R)/inst/lib/shiny; \
# 	fi
# 	mkdir -p $(PATH_PKG_R)/inst/lib/shiny
# 	cp -r $(PATH_PKG_JS)/dist/chat $(PATH_PKG_R)/inst/lib/shiny/
# 	cp -r $(PATH_PKG_JS)/dist/markdown-stream $(PATH_PKG_R)/inst/lib/shiny/
# 	(git rev-parse HEAD) > "$(PATH_PKG_R)/inst/lib/shiny/GIT_VERSION"

.PHONY: r-docs
r-docs: ## [r] Build R docs
	@echo "📖 Rendering R docs with pkgdown"
	cd $(PATH_PKG_R) && Rscript -e "pkgdown::build_site()"

.PHONY: r-docs-preview
r-docs-preview: ## [r] Build R docs
	@echo "📖 Rendering R docs with pkgdown"
	cd $(PATH_PKG_R) && Rscript -e "pkgdown::preview_site()"

.PHONY: py-setup
py-setup:  ## [py] Setup python environment
	uv sync --all-extras --all-groups --upgrade

.PHONY: py-check
py-check:  py-check-format py-check-types py-check-tests ## [py] Run python checks

.PHONY: py-check-tox
py-check-tox:  ## [py] Run python 3.9 - 3.12 checks with tox
	@echo ""
	@echo "🔄 Running tests and type checking with tox for Python 3.9--3.12"
	uv run tox run-parallel

.PHONY: py-check-tests
py-check-tests:  ## [py] Run python tests
	@echo ""
	@echo "🧪 Running tests with pytest"
	uv run pytest pkg-py/tests --ignore=pkg-py/tests/playwright

.PHONY: py-e2e-setup
py-e2e-setup:  ## [py] Install Playwright browsers for e2e tests
	@echo ""
	@echo "🎭 Installing Playwright browsers"
	uv run playwright install chromium

.PHONY: py-e2e-tests
py-e2e-tests:  ## [py] Run Playwright e2e tests (requires OPENAI_API_KEY)
	@echo ""
	@echo "🧪 Running Playwright e2e tests"
	uv run pytest pkg-py/tests/playwright -v -n auto

.PHONY: py-check-types
py-check-types:  ## [py] Run python type checks
	@echo ""
	@echo "📝 Checking types with pyright"
	uv run pyright

.PHONY: py-check-format
py-check-format:
	@echo ""
	@echo "📐 Checking format with ruff"
	uv run ruff check pkg-py --config pyproject.toml

.PHONY: py-format
py-format: ## [py] Format python code
	uv run ruff check --fix pkg-py --config pyproject.toml
	uv run ruff format pkg-py --config pyproject.toml

# .PHONY: py-coverage
# py-coverage: ## [py] Generate coverage report
# 	@echo "📔 Generating coverage report"
# 	uv run coverage run -m pytest
# 	uv run coverage report

# .PHONY: py-coverage-report
# py-coverage-report: py-coverage ## [py] Generate coverage report and open it in browser
# 	uv run coverage html
# 	@echo ""
# 	@echo "📡 Serving coverage report at http://localhost:8081/"
# 	@npx http-server htmlcov --silent -p 8081

# .PHONY: py-update-snaps
# py-update-snaps:  ## [py] Update python test snapshots
# 	@echo "📸 Updating pytest snapshots"
# 	uv run pytest --snapshot-update

.PHONY: py-docs
py-docs: py-docs-api py-docs-render ## [py] Build python docs

.PHONY: py-docs-render
py-docs-render:  ## [py] Render python docs
	@echo "📖 Rendering python docs with quarto"
	@$(eval export IN_QUARTODOC=true)
	${QUARTO_PATH} render pkg-py/docs

.PHONY: py-docs-preview
py-docs-preview:  ## [py] Preview python docs
	@echo "📖 Rendering python docs with quarto"
	@$(eval export IN_QUARTODOC=true)
	${QUARTO_PATH} preview pkg-py/docs

.PHONY: py-docs-api
py-docs-api:  ## [py] Update python API docs
	@echo "📖 Generating python docs with quartodoc"
	@$(eval export IN_QUARTODOC=true)
	cd pkg-py/docs && uv run quartodoc build
	cd pkg-py/docs && uv run quartodoc interlinks

.PHONY: py-docs-api-watch
py-docs-api-watch:  ## [py] Update python docs
	@echo "📖 Generating python docs with quartodoc"
	@$(eval export IN_QUARTODOC=true)
	uv run quartodoc build --config pkg-py/docs/_quarto.yml --watch

.PHONY: py-docs-clean
py-docs-clean:   ## [py] Clean python docs
	@echo "🧹 Cleaning python docs"
	rm -r pkg-py/docs/api
	find pkg-py/docs/py -name '*.quarto_ipynb' -delete

.PHONY: py-build
py-build:   ## [py] Build python package
	@echo "🧳 Building python package"
	@[ -d dist ] && rm -r dist || true
	uv build

.PHONY: py-update-dist
py-update-dist: ## [py] Update shinychat web assets
	@echo ""
	@echo "🔄 Updating shinychat web assets"
	if [ -d $(PATH_PKG_PY)/src/shinychat/www ]; then \
		rm -rf $(PATH_PKG_PY)/src/shinychat/www; \
	fi
	mkdir -p $(PATH_PKG_PY)/src/shinychat/www
	cp -r $(PATH_PKG_JS)/dist/chat $(PATH_PKG_PY)/src/shinychat/www/
	cp -r $(PATH_PKG_JS)/dist/markdown-stream $(PATH_PKG_PY)/src/shinychat/www/
	(git rev-parse HEAD) > "$(PATH_PKG_PY)/src/shinychat/www/GIT_VERSION"

.PHONY: help
help:  ## Show help messages for make targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; { \
		printf "\033[32m%-18s\033[0m", $$1; \
		if ($$2 ~ /^\[docs\]/) { \
			printf "\033[37m[docs]\033[0m%s\n", substr($$2, 7); \
		} else if ($$2 ~ /^\[py\]/) { \
			printf "  \033[31m[py]\033[0m%s\n", substr($$2, 5); \
		} else if ($$2 ~ /^\[r\]/) { \
			printf "   \033[34m[r]\033[0m%s\n", substr($$2, 4); \
		} else if ($$2 ~ /^\[js\]/) { \
			printf "  \033[33m[js]\033[0m%s\n", substr($$2, 5); \
		} else { \
			printf "       %s\n", $$2; \
		} \
	}'

.DEFAULT_GOAL := help

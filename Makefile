UV ?= uv
PYTHON ?= .venv/bin/python
CONTAINER_VENV ?= /tmp/ai-agent-systems-venv
CONTAINER_PYTHON ?= $(CONTAINER_VENV)/bin/python
PUBLISH_ENGINE ?= pandoc
# Metadata parsing must not require the Python environment that ``bootstrap``
# is responsible for creating.
BUILD_SYSTEM_VERSION := $(shell awk -F '[[:space:]]*=[[:space:]]*' '/^system_version[[:space:]]*=/ {gsub(/"/,"",$$2); print $$2; exit}' course.toml)
SOURCE_DATE_EPOCH := $(shell awk -F '[[:space:]]*=[[:space:]]*' '/^source_date_epoch[[:space:]]*=/ {print $$2; exit}' course.toml)

.PHONY: bootstrap bootstrap-check toolchain toolchain-canonical diagrams diagram-assets assemble quarto-config-qa \
        book site workbook slides build build-compat build-canonical examples labs test core-validate \
        lint coverage dependency-audit security-qa git-index-qa \
        book-qa pdf-structure-qa workbook-structure-qa slides-qa source-qa readme-qa source-lock-qa upstream-contract-qa l5-evidence-qa external-benchmark-contract-qa external-benchmark-preflight builder-lock-qa output-qa content-qa qa repo-qa validate validate-canonical \
        manifest release-checksums deterministic-packaging same-host-clean-rebuild reproducible release release-compat release-container release-container-inner source-clean clean

bootstrap:
	$(UV) sync --locked --all-groups --no-install-project
	@echo BOOTSTRAP_OK

bootstrap-check:
	$(UV) lock --check --offline

# Native compatibility path available on developer hosts.
toolchain:
	$(PYTHON) scripts/check_toolchain.py

toolchain-canonical:
	$(PYTHON) scripts/check_toolchain.py --canonical

diagrams:
	$(PYTHON) scripts/build_diagrams.py --update-svg

diagram-assets:
	$(PYTHON) scripts/build_diagrams.py

assemble:
	$(PYTHON) scripts/assemble_book.py

quarto-config-qa:
	$(PYTHON) scripts/qa_quarto_config.py

book:
	$(PYTHON) scripts/publish.py book --engine $(PUBLISH_ENGINE)

site:
	$(PYTHON) scripts/publish.py site --engine $(PUBLISH_ENGINE)

workbook:
	$(PYTHON) scripts/publish.py workbook --engine $(PUBLISH_ENGINE)

slides: diagram-assets
	$(PYTHON) scripts/build_slides.py

build: build-compat

build-compat:
	$(MAKE) PUBLISH_ENGINE=pandoc book site workbook slides

build-canonical:
	$(MAKE) PUBLISH_ENGINE=quarto book site workbook slides

examples:
	$(PYTHON) scripts/run_all_examples.py

labs:
	$(PYTHON) scripts/run_core_labs.py

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest -q tests

lint:
	$(PYTHON) -m ruff check src tests production experiments scripts examples labs

coverage:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest -q -p pytest_cov --cov=agentlab --cov=production.agentops_service --cov-report=term-missing --cov-report=xml:validation_logs/coverage.xml tests

dependency-audit:
	mkdir -p validation_logs
	$(PYTHON) -m pip_audit --local --format cyclonedx-json --output validation_logs/python-sbom.cdx.json

security-qa: lint coverage dependency-audit
	@echo SECURITY_QA_OK

git-index-qa:
	$(PYTHON) scripts/qa_git_index.py

core-validate: lint labs coverage examples

book-qa:
	$(PYTHON) scripts/qa_book.py

pdf-structure-qa:
	$(PYTHON) scripts/qa_pdf_structure.py

workbook-structure-qa:
	$(PYTHON) scripts/qa_workbook_structure.py

slides-qa:
	$(PYTHON) scripts/qa_slides.py

source-qa:
	$(PYTHON) scripts/qa_source.py

readme-qa:
	$(PYTHON) scripts/qa_readme.py

source-lock-qa:
	$(PYTHON) scripts/qa_source_lock_coverage.py

upstream-contract-qa:
	$(PYTHON) scripts/qa_upstream_contracts.py

l5-evidence-qa:
	$(PYTHON) scripts/qa_l5_evidence.py

external-benchmark-contract-qa:
	$(PYTHON) scripts/qa_external_benchmark_contracts.py

# Readiness only. A non-zero exit is expected on hosts without Docker,
# provider credentials, or a reset self-hosted WebArena stack.
external-benchmark-preflight:
	$(PYTHON) scripts/preflight_external_benchmarks.py

builder-lock-qa:
	$(PYTHON) scripts/qa_builder_contract.py

output-qa:
	$(PYTHON) scripts/qa_outputs.py

content-qa:
	$(PYTHON) scripts/qa_content_semantics.py

qa: source-qa readme-qa source-lock-qa upstream-contract-qa l5-evidence-qa external-benchmark-contract-qa builder-lock-qa quarto-config-qa book-qa pdf-structure-qa workbook-structure-qa slides-qa output-qa content-qa

repo-qa:
	$(PYTHON) scripts/validate_repo.py

validate: bootstrap-check toolchain core-validate build-compat qa repo-qa
	@echo VALIDATION_OK

validate-canonical: bootstrap-check toolchain-canonical core-validate build-canonical qa repo-qa
	@echo CANONICAL_VALIDATION_OK

manifest:
	$(PYTHON) scripts/generate_manifest.py

release-checksums:
	$(PYTHON) scripts/verify_release_checksums.py

deterministic-packaging:
	$(PYTHON) scripts/verify_deterministic_packaging.py

same-host-clean-rebuild:
	$(PYTHON) scripts/verify_same_host_clean_rebuild.py

# Backward-compatible alias; this target proves packaging determinism only.
reproducible: deterministic-packaging
	@echo REPRODUCIBLE_ALIAS_SCOPE=PACKAGING_ONLY

source-clean:
	$(PYTHON) scripts/verify_source_clean.py

release: release-compat

release-compat: validate manifest
	RELEASE_ENGINE=pandoc-compatibility $(PYTHON) scripts/build_release.py
	$(PYTHON) scripts/verify_release_checksums.py
	$(PYTHON) scripts/verify_source_clean.py
	$(PYTHON) scripts/verify_deterministic_packaging.py
	$(PYTHON) scripts/verify_same_host_clean_rebuild.py
	@echo RELEASE_COMPAT_OK

# Internal entrypoint for the pinned Linux builder.  Its virtual environment
# lives outside the bind-mounted source tree, so a macOS/Windows host .venv can
# never be executed or overwritten by the container.
release-container-inner: bootstrap validate-canonical manifest
	RELEASE_ENGINE=quarto-canonical $(PYTHON) scripts/build_release.py
	$(PYTHON) scripts/verify_release_checksums.py
	$(PYTHON) scripts/verify_source_clean.py
	$(PYTHON) scripts/verify_deterministic_packaging.py
	$(PYTHON) scripts/verify_same_host_clean_rebuild.py
	@echo RELEASE_CONTAINER_INNER_OK

release-container:
	docker build --file Dockerfile.builder --tag ai-agent-systems-builder:$(BUILD_SYSTEM_VERSION) .
	docker run --rm -e SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) -e UV_PROJECT_ENVIRONMENT=$(CONTAINER_VENV) -v "$$PWD:/workspace" -w /workspace ai-agent-systems-builder:$(BUILD_SYSTEM_VERSION) make PYTHON=$(CONTAINER_PYTHON) release-container-inner
	@echo RELEASE_CONTAINER_OK

clean:
	rm -rf .build .agentlab .pytest_cache validation_logs book/build workbook/build site dist
	rm -f book/zh/book.md slides/*.pptx slides/*.pdf MANIFEST.md
	rm -f book/assets/diagrams/*.png
	rm -rf book/assets/diagrams/pdf
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

# theme-producer — fresh-clone rebuild with make.
#
# Fresh machine path:
#   1. `make sync`     (uv-managed env from the committed lock)
#   2. `make test`     (pytest; skip reasons are printed)
#   3. `make gates`    (test + lint + hermetic + lock-check + docs-check)
#   4. `make build`    (sdist + wheel in dist/)
#
# Every target is anchored on $(CURDIR); none assumes a parent checkout.

UV     ?= uv
PYTHON := $(CURDIR)/.venv/bin/python

# The authoritative gate set. `make gates` runs it for a developer; CI runs one
# job per member (`.github/workflows/gates.yml`) and `make ci-gates-parity`
# fails when the two sets differ. Add a gate here AND a job there in one commit.
# `image` is added by REQ-011 and declared CI-only until then.
GATES := test lint hermetic lock-check docs-check

.PHONY: help sync install test lint format check gates hermetic lock-check docs-check build ci-gates-parity clean

help:
	@echo "sync            Install the env from uv.lock (uv sync --frozen)"
	@echo "test            Run the test suite (skip reasons shown)"
	@echo "lint            Ruff check src/"
	@echo "format          Ruff format src/"
	@echo "check           Alias of lint (in-tree name)"
	@echo "hermetic        Run the suite with empty HOME/XDG and a foreign cwd"
	@echo "lock-check      uv lock --check (the committed lock is current)"
	@echo "docs-check      README/CHANGELOG/LICENSE/AGENTS + CLAUDE symlink exist"
	@echo "gates           $(GATES)"
	@echo "ci-gates-parity Workflow jobs equal GATES + declared CI-only jobs"
	@echo "build           Build sdist + wheel into dist/"
	@echo "install         Install the built package into .venv"
	@echo "clean           Remove dist/ and local caches"

sync:
	$(UV) sync --frozen

install: sync
	$(UV) pip install --reinstall .

# -rs prints every skip with its reason: engine-dependent tests skip honestly
# when no engine is reachable, they are never silently absent.
test:
	$(UV) run pytest -q -rs

lint:
	$(UV) run ruff check src

format:
	$(UV) run ruff format src

check: lint

# Pass with HOME and all four XDG roots pointing at empty temp dirs and an
# unrelated working directory. The chdir itself is the autouse fixture's job
# (tests/conftest.py); the canary proves it runs.
hermetic:
	@test -x "$(PYTHON)" || { echo "run 'make sync' first"; exit 1; }
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp" 2>/dev/null || true' EXIT; \
	env HOME="$$tmp" \
	    XDG_CONFIG_HOME="$$tmp/config" XDG_CACHE_HOME="$$tmp/cache" \
	    XDG_DATA_HOME="$$tmp/data" XDG_STATE_HOME="$$tmp/state" \
	    TMPDIR="$$tmp" \
	    "$(PYTHON)" -m pytest -q -rs

lock-check:
	$(UV) lock --check

docs-check:
	@test -f README.md      || { echo "missing README.md"; exit 1; }
	@test -f CHANGELOG.md   || { echo "missing CHANGELOG.md"; exit 1; }
	@test -f LICENSE        || { echo "missing LICENSE"; exit 1; }
	@test -f AGENTS.md      || { echo "missing AGENTS.md"; exit 1; }
	@test -L CLAUDE.md      || { echo "CLAUDE.md must be a symlink to AGENTS.md"; exit 1; }
	@test "$$(readlink CLAUDE.md)" = "AGENTS.md" || { echo "CLAUDE.md must point to AGENTS.md"; exit 1; }
	@grep -q "MIT License" LICENSE || { echo "LICENSE is not the MIT text"; exit 1; }

gates: $(GATES)

ci-gates-parity:
	python3 scripts/ci-gates-parity.py

build:
	$(UV) build

clean:
	rm -rf dist .pytest_cache .ruff_cache .coverage htmlcov build
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

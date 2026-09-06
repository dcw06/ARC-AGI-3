# ARC Prize 2026 — ARC-AGI-3 local dev workflow.
#
# Five commands cover the whole loop:
#   make setup        # one-time: venv + arc-agi + clone framework
#   make play-local   # fast inner loop: run agent/my_agent.py on a real game
#   make pull-sample  # fetch the official Stochastic Goose sample for reference
#   make submit       # build notebook from agent/my_agent.py + push to Kaggle
#   make status       # tail the latest Kaggle run

UV              ?= uv
VENV            := .venv
VENV_PY         := $(VENV)/bin/python
VENV_PIP        := $(VENV)/bin/pip
UV_CACHE_DIR    := $(CURDIR)/.uv-cache
UV_PYTHON_DIR   := $(CURDIR)/.uv-python
UV_ENV          := UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PYTHON_INSTALL_DIR=$(UV_PYTHON_DIR) UV_PYTHON_INSTALL_BIN=0
PROJECT_CACHE   := $(CURDIR)/.cache
PYTHON_ENV      := MPLCONFIGDIR=$(PROJECT_CACHE)/matplotlib XDG_CACHE_HOME=$(PROJECT_CACHE) KAGGLE_CONFIG_DIR=$(CURDIR)/.kaggle
# Read the project-local token at recipe time and expose it as KAGGLE_API_TOKEN
# (the only env var the modern Kaggle CLI honours for token auth).
KAGGLE          := $(PYTHON_ENV) KAGGLE_API_TOKEN=$$(cat .kaggle/access_token) $(VENV)/bin/kaggle
FRAMEWORK_REPO  := https://github.com/arcprize/ARC-AGI-3-Agents.git
FRAMEWORK_DIR   := vendor/ARC-AGI-3-Agents
FRAMEWORK_REV   := 4743e7d0aaae0ded0d98a89a7e282e63564cd58b
ARC_AGI_VERSION := 0.9.9
ARCENGINE_VERSION := 0.9.3
COMP_SLUG       := arc-prize-2026-arc-agi-3
GAME            ?=
STEPS           ?= 200

.PHONY: help setup play-local play-competition-like pull-sample notebook submit status verify-local validate-phase0 test clean _check-kaggle

_check-kaggle:
	@if [ ! -s .kaggle/access_token ]; then \
	    echo "ERROR: .kaggle/access_token is missing or empty."; \
	    echo "       Generate a token at https://www.kaggle.com/settings (API → Create New Token)"; \
	    echo "       and save it as a one-line file at: $(PWD)/.kaggle/access_token"; \
	    exit 1; \
	fi

help:
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-15s %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Vars: GAME=$(GAME)  STEPS=$(STEPS)"

setup: ## One-time install: managed Python 3.12, venv, dependencies, framework
	mkdir -p $(UV_CACHE_DIR) $(UV_PYTHON_DIR) $(PROJECT_CACHE)/matplotlib .kaggle
	$(UV_ENV) $(UV) venv --python 3.12 --managed-python $(VENV)
	$(UV_ENV) $(UV) pip install --python $(VENV_PY) \
		"arc-agi==$(ARC_AGI_VERSION)" "arcengine==$(ARCENGINE_VERSION)" \
		"kaggle==2.2.4" "python-dotenv==1.2.3" "pandas==3.0.5" "pyarrow==25.0.1"
	@if [ ! -d "$(FRAMEWORK_DIR)/.git" ]; then \
	    mkdir -p vendor && git clone $(FRAMEWORK_REPO) $(FRAMEWORK_DIR); \
	fi
	@git -C $(FRAMEWORK_DIR) fetch --depth 1 origin $(FRAMEWORK_REV)
	@git -C $(FRAMEWORK_DIR) checkout --detach $(FRAMEWORK_REV)
	@# Slim agents/__init__.py so we don't need langgraph/langsmith/smolagents/etc.
	@# (Same trick the official Stochastic Goose sample uses on Kaggle.)
	@$(PYTHON_ENV) $(VENV_PY) scripts/slim_framework.py
	@echo ""
	@echo "Setup complete. Try:  make play-local"

play-local: ## Run the Plan 8 adapter locally (GAME=ls20 optional)
	$(PYTHON_ENV) $(VENV_PY) scripts/play_competition_like.py --backend local $(if $(GAME),--game $(GAME)) --max-actions $(STEPS)

verify-local: ## Quick smoke test: 50 steps on ls20 + vc33 only
	$(PYTHON_ENV) $(VENV_PY) scripts/play_competition_like.py --backend local --game ls20,vc33 --max-actions 50

play-competition-like: ## Run the Plan 8 adapter locally (GAME=ls20 optional)
	$(PYTHON_ENV) $(VENV_PY) scripts/play_competition_like.py --backend local $(if $(GAME),--game $(GAME)) --max-actions $(STEPS)

test: ## Run project unit and integration tests
	$(PYTHON_ENV) $(VENV_PY) -m unittest discover -s tests -v

validate-phase0: test ## Validate Plan 8 Phase 0 configuration and activation gates
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase0.py

list-games: ## Show all available games
	$(PYTHON_ENV) $(VENV_PY) scripts/play_local.py --list

pull-sample: _check-kaggle ## Download the official Stochastic Goose sample notebook for reference
	mkdir -p reference/stochastic-goose
	$(KAGGLE) kernels pull inversion/arc3-sample-submission-stochastic-goose \
	    -p reference/stochastic-goose -m
	@echo "Open reference/stochastic-goose/*.ipynb for the canonical pattern."

notebook: ## Splice agent/my_agent.py into notebooks/submission.ipynb
	$(PYTHON_ENV) $(VENV_PY) scripts/build_notebook.py

submit: notebook _check-kaggle ## Build notebook and push to Kaggle (one-line submission)
	@grep -q REPLACE_WITH_YOUR_USERNAME notebooks/kernel-metadata.json && { \
	    echo "ERROR: edit notebooks/kernel-metadata.json and replace REPLACE_WITH_YOUR_USERNAME"; \
	    exit 1; } || true
	$(KAGGLE) kernels push -p notebooks/
	@echo ""
	@echo "Pushed. Track it with:  make status"

status: _check-kaggle ## Show the status of your most recent Kaggle kernel run
	@KERNEL_ID=$$($(VENV_PY) -c "import json; print(json.load(open('notebooks/kernel-metadata.json'))['id'])"); \
	$(KAGGLE) kernels status $$KERNEL_ID

clean: ## Remove generated artefacts (venv, downloaded games, vendored repos)
	rm -rf $(VENV) .cache .uv-cache .uv-python vendor environment_files recordings notebooks/submission.ipynb \
	       reference logs.log __pycache__ .pytest_cache

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

.PHONY: help setup play-local play-competition-like phase2-diagnostic-replay pull-sample notebook m0-notebook m0-notebooks m0-q3vl30-notebook m0-q3vl8-notebook m0-q3vl30-push m0-q3vl8-push e1-q3vl30-notebook e1-q3vl30-push e1-q3vl30-status e1-q3vl30-output e1-four-cell-notebook e1-four-cell-push e1-four-cell-status e1-four-cell-output validate-e1-four-cell submit status verify-local validate-gateway validate-phase0 validate-phase0f validate-m0-exit validate-phase1 validate-phase2-contract validate-phase2-selection validate-phase2-conditional test clean _check-kaggle

_check-kaggle:
	@$(VENV_PY) scripts/check_kaggle_config.py

help:
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-15s %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Vars: GAME=$(GAME)  STEPS=$(STEPS)"

setup: ## One-time install: managed Python 3.12, venv, dependencies, framework
	mkdir -p $(UV_CACHE_DIR) $(UV_PYTHON_DIR) $(PROJECT_CACHE)/matplotlib .kaggle
	$(UV_ENV) $(UV) venv --python 3.12 --managed-python $(VENV)
	$(UV_ENV) $(UV) pip install --python $(VENV_PY) \
		"arc-agi==$(ARC_AGI_VERSION)" "arcengine==$(ARCENGINE_VERSION)" \
		"requests==2.34.2" "numpy==2.5.2" "pydantic==2.13.5" \
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

phase2-diagnostic-replay: ## Replay diagnostics at DIAGNOSTICS=reports/phase2-diagnostics
	$(PYTHON_ENV) $(VENV_PY) scripts/replay_phase2_diagnostics.py $(or $(DIAGNOSTICS),reports/phase2-diagnostics) --require-failure

test: ## Run project unit and integration tests
	$(PYTHON_ENV) $(VENV_PY) -m unittest discover -s tests -v

validate-gateway: ## Exercise production transport against pinned local REST gateway
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_local_gateway.py

validate-phase0: test ## Validate Plan 8 Phase 0 configuration and activation gates
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase0.py

validate-phase0f: test ## Validate Phase 0F foundation and report remaining M0 work
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase0f.py

validate-m0-exit: validate-phase0f ## Require all target profiles and the provisional M0 selection
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_m0_exit.py

validate-phase1: test ## Validate Phase 1 implementation, evidence, decision, and exit gate
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase1.py

validate-phase2-contract: test ## Validate frozen Phase 2 admission contract without activating treatment
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase2_contract.py

validate-phase2-selection: validate-phase2-contract ## Validate evidence review and treatment/no-treatment decision
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase2_selection.py

validate-phase2-conditional: validate-phase2-selection ## Prove no unselected E2/E3/E4 implementation leaked into E1
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase2_conditional.py

.PHONY: phase2-cd82-notebook phase2-cd82-push phase2-cd82-status phase2-cd82-output
phase2-cd82-notebook: ## Build the private two-run parent diagnostic notebook
	$(PYTHON_ENV) $(VENV_PY) scripts/build_phase2_diagnostic_notebook.py

phase2-cd82-push: phase2-cd82-notebook _check-kaggle ## Run two cd82 parent diagnostics; no scored submission
	$(KAGGLE) kernels push -p notebooks/phase2-cd82 --accelerator NvidiaRtxPro6000

phase2-cd82-status: _check-kaggle ## Check the two-run diagnostic notebook
	$(KAGGLE) kernels status daichongwei06/arc3-phase2-cd82-diagnostics

phase2-cd82-output: _check-kaggle ## Download parent diagnostic evidence
	mkdir -p reports/runs/phase2-cd82
	$(KAGGLE) kernels output daichongwei06/arc3-phase2-cd82-diagnostics -p reports/runs/phase2-cd82

.PHONY: validate-phase2-reproduction
.PHONY: phase2-budget phase2-cd82-v2-notebook
phase2-budget: ## Show cumulative Phase 2 charges, reservations and unresolved inventory
	$(PYTHON_ENV) $(VENV_PY) scripts/phase2_budget.py status

phase2-cd82-v2-notebook: ## Build inactive V2 full-sequence capture; never uploads or starts compute
	$(PYTHON_ENV) $(VENV_PY) scripts/build_phase2_diagnostic_notebook_v2.py

validate-phase2-reproduction: ## Validate downloaded two-run evidence against the pre-launch source lock
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_phase2_reproduction.py reports/runs/phase2-cd82/phase2-cd82

list-games: ## Show all available games
	$(PYTHON_ENV) $(VENV_PY) scripts/play_local.py --list

pull-sample: _check-kaggle ## Download the official Stochastic Goose sample notebook for reference
	mkdir -p reference/stochastic-goose
	$(KAGGLE) kernels pull inversion/arc3-sample-submission-stochastic-goose \
	    -p reference/stochastic-goose -m
	@echo "Open reference/stochastic-goose/*.ipynb for the canonical pattern."

notebook: ## Splice agent/my_agent.py into notebooks/submission.ipynb
	$(PYTHON_ENV) $(VENV_PY) scripts/build_notebook.py

m0-notebook: ## Build the first target-RTX M0 profiling notebook locally
	$(PYTHON_ENV) $(VENV_PY) scripts/build_m0_profile_notebook.py --candidate q38

m0-q3vl30-notebook: ## Build the sparse 30B-A3B target-RTX M0 profile
	$(PYTHON_ENV) $(VENV_PY) scripts/build_m0_profile_notebook.py --candidate q3vl30

m0-q3vl8-notebook: ## Build the 8B target-RTX M0 fallback profile
	$(PYTHON_ENV) $(VENV_PY) scripts/build_m0_profile_notebook.py --candidate q3vl8

m0-notebooks: m0-notebook m0-q3vl30-notebook m0-q3vl8-notebook ## Build all frozen M0 profiles

m0-q3vl30-push: m0-q3vl30-notebook _check-kaggle ## Run the 30B M0 profile on the target RTX
	$(KAGGLE) kernels push -p notebooks/m0-q3vl30 --accelerator NvidiaRtxPro6000

m0-q3vl8-push: m0-q3vl8-notebook _check-kaggle ## Run the 8B M0 profile on the target RTX
	$(KAGGLE) kernels push -p notebooks/m0-q3vl8 --accelerator NvidiaRtxPro6000

e1-q3vl30-notebook: ## Build the unscored mixed E1 profile for the selected 30B model
	$(PYTHON_ENV) $(VENV_PY) scripts/build_e1_profile_notebook.py

e1-q3vl30-push: e1-q3vl30-notebook _check-kaggle ## Run the mixed E1 profile on target RTX (not scored)
	$(KAGGLE) kernels push -p notebooks/e1-q3vl30 --accelerator NvidiaRtxPro6000

e1-q3vl30-status: _check-kaggle ## Check the private mixed E1 profile run
	$(KAGGLE) kernels status daichongwei06/arc3-e1-q3vl30-mixed-profile

e1-q3vl30-output: _check-kaggle ## Download the completed mixed E1 profile evidence
	mkdir -p reports/runs/e1-q3vl30
	$(KAGGLE) kernels output daichongwei06/arc3-e1-q3vl30-mixed-profile -p reports/runs/e1-q3vl30

e1-four-cell-notebook: ## Build the private counterbalanced whole-run E1 notebook
	$(PYTHON_ENV) $(VENV_PY) scripts/build_e1_four_cell_notebook.py

e1-four-cell-push: e1-four-cell-notebook _check-kaggle ## Run the whole-run four-cell experiment on target RTX (not scored)
	$(KAGGLE) kernels push -p notebooks/e1-four-cell --accelerator NvidiaRtxPro6000

e1-four-cell-status: _check-kaggle ## Check the private whole-run E1 run
	$(KAGGLE) kernels status daichongwei06/arc3-e1-causal-four-cell

e1-four-cell-output: _check-kaggle ## Download the whole-run E1 evidence
	mkdir -p reports/runs/e1-four-cell
	$(KAGGLE) kernels output daichongwei06/arc3-e1-causal-four-cell -p reports/runs/e1-four-cell

validate-e1-four-cell: ## Validate the downloaded counterbalanced whole-run E1 result
	$(PYTHON_ENV) $(VENV_PY) scripts/validate_e1_whole_run.py

submit: notebook _check-kaggle ## Build notebook and push to Kaggle (one-line submission)
	@grep -q REPLACE_WITH_YOUR_USERNAME notebooks/kernel-metadata.json && { \
	    echo "ERROR: edit notebooks/kernel-metadata.json and replace REPLACE_WITH_YOUR_USERNAME"; \
	    exit 1; } || true
	$(KAGGLE) kernels push -p notebooks/ --accelerator NvidiaRtxPro6000
	@echo ""
	@echo "Pushed. Track it with:  make status"

status: _check-kaggle ## Show the status of your most recent Kaggle kernel run
	@KERNEL_ID=$$($(VENV_PY) -c "import json; print(json.load(open('notebooks/kernel-metadata.json'))['id'])"); \
	$(KAGGLE) kernels status $$KERNEL_ID

clean: ## Remove generated artefacts (venv, downloaded games, vendored repos)
	rm -rf $(VENV) .cache .uv-cache .uv-python vendor environment_files recordings notebooks/submission.ipynb \
	       notebooks/m0-*/profile.ipynb reference logs.log __pycache__ .pytest_cache

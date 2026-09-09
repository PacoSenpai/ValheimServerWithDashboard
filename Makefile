SHELL := /bin/bash

PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip

BACKEND  := backend
FRONTEND := frontend

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend \
        lint lint-backend lint-frontend test test-backend test-frontend build \
        clean fake-server requirements

help:
	@echo "Targets:"
	@echo "  make install          Backend (venv + deps) + frontend (npm install)"
	@echo "  make dev              Backend (uvicorn) + frontend (vite) + fake server"
	@echo "  make lint             ruff + mypy + eslint + tsc --noEmit"
	@echo "  make test             pytest + vitest"
	@echo "  make build            frontend production build"
	@echo "  make fake-server      ejecuta el servidor falso para desarrollo"
	@echo "  make requirements     regenera requirements.lock desde pyproject"

install: install-backend install-frontend

install-backend:
	$(PYTHON) -m venv $(BACKEND)/.venv
	$(BACKEND)/.venv/bin/python -m pip install --upgrade pip wheel
	$(BACKEND)/.venv/bin/python -m pip install -e $(BACKEND)[dev]

install-frontend:
	cd $(FRONTEND) && npm install

requirements:
	$(BACKEND)/.venv/bin/python -m piptools compile --output-file=$(BACKEND)/requirements.lock $(BACKEND)/pyproject.toml

dev:
	@trap 'kill 0' SIGINT; \
	$(MAKE) -j3 dev-backend dev-frontend fake-server

dev-backend:
	$(BACKEND)/.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8080 --app-dir $(BACKEND)

dev-frontend:
	cd $(FRONTEND) && npm run dev

fake-server:
	$(PYTHON) tools/fake-valheim-server.py

lint: lint-backend lint-frontend

lint-backend:
	$(BACKEND)/.venv/bin/ruff check $(BACKEND)
	cd $(BACKEND) && .venv/bin/mypy

lint-frontend:
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npx tsc --noEmit

test: test-backend test-frontend

test-backend:
	$(BACKEND)/.venv/bin/pytest -q $(BACKEND)/tests

test-frontend:
	cd $(FRONTEND) && npm test -- --run

build:
	cd $(FRONTEND) && npm run build

clean:
	rm -rf $(BACKEND)/.venv $(FRONTEND)/node_modules $(FRONTEND)/dist
	rm -rf .pytest_cache .ruff_cache $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache
	rm -rf $(BACKEND)/data/*.sqlite* $(BACKEND)/data/logs/*.log

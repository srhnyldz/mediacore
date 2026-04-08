PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
COMPOSE ?= docker compose

.PHONY: venv install test compile up down logs smoke

venv:
	python3 -m venv .venv

install: venv
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest tests

compile:
	$(PYTHON) -m compileall app tests scripts

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api worker redis

smoke:
	$(PYTHON) scripts/smoke_task_flow.py --url "$(URL)"

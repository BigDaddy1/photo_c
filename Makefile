COMPOSE := docker compose
PYTHON ?= python3
HARD ?= 0

ifneq ($(filter --hard,$(MAKECMDGOALS)),)
HARD := 1
endif

.PHONY: help run stop test lint demo drop --hard

help:
	@printf '%s\n' \
		'make run                 Build and run the API and PostgreSQL containers.' \
		'make stop                Stop PhotoColor containers while preserving data.' \
		'make test                Build the test image, start PostgreSQL, and run pytest.' \
		'make lint                Run Ruff in the test image.' \
		'make demo                Start the stack and run the endpoint smoke test.' \
		'make drop                Remove PhotoColor containers, network, and local image.' \
		'make drop HARD=1         Also remove PostgreSQL and image-storage volumes.' \
		'make drop -- --hard      Equivalent hard-drop form.'

run:
	@$(COMPOSE) up --build

stop:
	@$(COMPOSE) down --remove-orphans

test:
	@$(COMPOSE) --profile test up --build --abort-on-container-exit --exit-code-from test test

lint:
	@$(COMPOSE) --profile test run --rm --no-deps --build test ruff check .

demo:
	@$(COMPOSE) up --build -d
	@attempt=0; until curl -fsS http://localhost:8000/health >/dev/null; do \
		attempt=$$((attempt + 1)); \
		if [ $$attempt -ge 30 ]; then echo 'API did not become healthy within 30 seconds.' >&2; exit 1; fi; \
		sleep 1; \
	done
	@$(PYTHON) scripts/demo_api.py

drop:
ifeq ($(HARD),1)
	@$(COMPOSE) down --remove-orphans --rmi local --volumes
else
	@$(COMPOSE) down --remove-orphans --rmi local
endif

--hard:
	@:

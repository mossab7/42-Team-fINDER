SHELL := /bin/sh
COMPOSE ?= docker compose

.DEFAULT_GOAL := help

.PHONY: help up public-up down restart rebuild logs status test test-backend test-frontend

help:
	@printf '%s\n' \
		'42 Team Finder commands:' \
		'  make up             Build and start the application' \
		'  make public-up      Start the HTTPS public deployment profile' \
		'  make down           Stop the application' \
		'  make restart        Restart running services' \
		'  make rebuild        Rebuild and recreate all services' \
		'  make logs           Follow application logs' \
		'  make status         Show service health' \
		'  make test           Run all backend and frontend checks' \
		'  make test-backend   Run the backend tests' \
		'  make test-frontend  Run frontend tests, lint, and build'

.env:
	cp .env.example .env
	@printf '%s\n' 'Created .env from .env.example. Add 42 credentials for live data; blank credentials use demo mode.'

up: .env
	$(COMPOSE) up --build -d
	@printf '%s\n' '42 Team Finder is available at http://localhost:3000'

public-up: .env
	FRONTEND_PORT=3000 HTTP_PORT=80 HTTPS_PORT=443 $(COMPOSE) --profile public up --build -d
	@printf '%s\n' '42 Team Finder is available at the HTTPS URL in PUBLIC_BASE_URL'

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

rebuild: .env
	$(COMPOSE) up --build --force-recreate -d
	@printf '%s\n' '42 Team Finder was rebuilt at http://localhost:3000'

logs:
	$(COMPOSE) logs --follow --tail=100

status:
	$(COMPOSE) ps

test: test-backend test-frontend

test-backend:
	docker build -t team-finder-backend-test -f backend/Dockerfile backend
	docker run --rm --user root -e PYTHONPATH=/app -v "$(CURDIR)/backend:/app" -w /app team-finder-backend-test sh -c "pip install -q -r requirements-dev.txt && pytest -q"

test-frontend:
	docker build --target build -t team-finder-frontend-test frontend
	docker run --rm -v "$(CURDIR)/frontend/src:/app/src:ro" team-finder-frontend-test npm test -- --run
	docker run --rm team-finder-frontend-test npm run lint
	docker run --rm team-finder-frontend-test npm run build

.PHONY: env up down restart logs ps shell migrations migrate seed schools test lint typecheck front-build

DC = docker compose
BACKEND = $(DC) exec backend

# ---------- Docker ----------
env:            ## создать .env из шаблона (если его ещё нет)
	@test -f .env || cp .env.example .env

up: env         ## поднять всё: db, redis, backend, worker, frontend, mailhog
	$(DC) up -d --build

down:
	$(DC) down

restart:
	$(DC) restart backend worker frontend

logs:
	$(DC) logs -f --tail=100

ps:
	$(DC) ps

shell:          ## Django shell внутри контейнера
	$(BACKEND) python manage.py shell

# ---------- Backend (выполняется в контейнере backend) ----------
migrations:
	$(BACKEND) python manage.py makemigrations

migrate:
	$(BACKEND) python manage.py migrate

seed:
	$(BACKEND) python seed_data.py

schools:        ## справочник школ: встроенный снимок OSM (или: make schools ARGS=--osm / ARGS=путь.csv)
	$(BACKEND) python manage.py import_schools $(ARGS)

test:
	$(BACKEND) pytest -v

lint:
	$(BACKEND) ruff check .

typecheck:
	$(BACKEND) mypy .

# ---------- Frontend ----------
front-build:
	$(DC) exec frontend npm run build

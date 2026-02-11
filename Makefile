.PHONY: help setup start stop restart logs clean init-db status load-data generate-dataset test

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Rakuten MLOps - Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup: copy env file and create directories
	@echo "$(BLUE)Setting up project...$(NC)"
	@if [ ! -f .env ]; then \
		cp env.example.txt .env; \
		echo "$(GREEN)Created .env file (please edit with your credentials)$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi
	@mkdir -p data/raw data/training_snapshots dags logs
	@echo "$(GREEN)Setup complete!$(NC)"

start: ## Start infrastructure stack (Postgres, MLflow, MinIO, Airflow)
	@echo "$(BLUE)Starting infrastructure services...$(NC)"
	docker compose -f docker-compose.infrastructure.yml up -d
	@echo "$(GREEN)Infrastructure started!$(NC)"
	@echo "$(YELLOW)Airflow UI: http://localhost:8080 (admin/admin)$(NC)"
	@echo "$(YELLOW)MLflow UI: http://localhost:5000$(NC)"
	@echo "$(YELLOW)MinIO UI: http://127.0.0.1:9001$(NC)"

stop: ## Stop infrastructure stack
	@echo "$(BLUE)Stopping infrastructure services...$(NC)"
	docker compose -f docker-compose.infrastructure.yml down
	@echo "$(GREEN)Infrastructure stopped!$(NC)"

start-api: ## Start API stack (Postgres, MLflow, FastAPI)
	@echo "$(BLUE)Starting API services...$(NC)"
	docker compose -f docker-compose.api.yml up -d --build
	@echo "$(GREEN)API services started!$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)API Docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)MLflow UI: http://localhost:5000$(NC)"

stop-api: ## Stop API stack
	@echo "$(BLUE)Stopping API services...$(NC)"
	docker compose -f docker-compose.api.yml down
	@echo "$(GREEN)API services stopped!$(NC)"

start-monitor: ## Start monitoring stack (Prometheus, Grafana)
	@echo "$(BLUE)Starting monitoring services...$(NC)"
	docker compose -f docker-compose.monitor.yml up -d
	@echo "$(GREEN)Monitoring services started!$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/admin)$(NC)"

stop-monitor: ## Stop monitoring stack
	@echo "$(BLUE)Stopping monitoring services...$(NC)"
	docker compose -f docker-compose.monitor.yml down
	@echo "$(GREEN)Monitoring services stopped!$(NC)"

start-full: ## Start all stacks (Infrastructure + API + Monitoring)
	@echo "$(BLUE)Starting full stack...$(NC)"
	docker compose -f docker-compose.full.yml up -d --build
	@echo "$(GREEN)Full stack started!$(NC)"
	@echo "$(YELLOW)Airflow UI: http://localhost:8080 (admin/admin)$(NC)"
	@echo "$(YELLOW)MLflow UI: http://localhost:5000$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/admin)$(NC)"

stop-full: ## Stop all stacks
	@echo "$(BLUE)Stopping full stack...$(NC)"
	docker compose -f docker-compose.full.yml down
	@echo "$(GREEN)Full stack stopped!$(NC)"

restart-api: stop-api start-api ## Restart API stack

restart-monitor: stop-monitor start-monitor ## Restart monitoring stack

restart-full: stop-full start-full ## Restart full stack

restart: stop start ## Restart all services

ps: ## Show running containers (infrastructure)
	docker compose -f docker-compose.infrastructure.yml ps

ps-all: ## Show all running containers (all stacks)
	@echo "$(BLUE)Infrastructure Stack:$(NC)"
	@docker compose -f docker-compose.infrastructure.yml ps 2>/dev/null || echo "Not running"
	@echo ""
	@echo "$(BLUE)API Stack:$(NC)"
	@docker compose -f docker-compose.api.yml ps 2>/dev/null || echo "Not running"
	@echo ""
	@echo "$(BLUE)Monitoring Stack:$(NC)"
	@docker compose -f docker-compose.monitor.yml ps 2>/dev/null || echo "Not running"

logs: ## Show logs from infrastructure services
	docker compose -f docker-compose.infrastructure.yml logs -f

logs-api: ## Show API service logs
	docker compose -f docker-compose.api.yml logs -f api

logs-monitor: ## Show monitoring service logs
	docker compose -f docker-compose.monitor.yml logs -f

logs-airflow: ## Show Airflow scheduler logs
	docker logs -f rakuten_airflow_scheduler

logs-mlflow: ## Show MLflow logs
	docker logs -f rakuten_mlflow

logs-postgres: ## Show PostgreSQL logs
	docker logs -f rakuten_postgres

init-db: ## Initialize database with 40% of data
	@echo "$(BLUE)Initializing database...$(NC)"
	docker exec rakuten_airflow_webserver bash -c "pip install -r /requirements.txt && python /opt/airflow/src/data/db_init.py"
	@echo "$(GREEN)Database initialized!$(NC)"

status: ## Show current data loading status
	@echo "$(BLUE)Checking current status...$(NC)"
	docker exec rakuten_airflow_webserver python /opt/airflow/src/data/loader.py --status

history: ## Show data loading history
	@echo "$(BLUE)Loading history...$(NC)"
	docker exec rakuten_airflow_webserver python /opt/airflow/src/data/loader.py --history

load-data: ## Load next increment of data (3%)
	@echo "$(BLUE)Loading next data increment...$(NC)"
	docker exec rakuten_airflow_webserver python /opt/airflow/src/data/loader.py
	@echo "$(GREEN)Data loaded!$(NC)"

generate-dataset: ## Generate balanced dataset
	@echo "$(BLUE)Generating balanced dataset...$(NC)"
	docker exec rakuten_airflow_webserver python /opt/airflow/src/data/dataset_generator.py
	@echo "$(GREEN)Dataset generated!$(NC)"

test-config: ## Test configuration
	@echo "$(BLUE)Testing configuration...$(NC)"
	docker exec rakuten_airflow_webserver python /opt/airflow/src/config.py

shell-airflow: ## Open shell in Airflow container
	docker exec -it rakuten_airflow_webserver bash

shell-postgres: ## Open PostgreSQL shell
	docker exec -it rakuten_postgres psql -U rakuten_user -d rakuten_db

clean: ## Remove all containers and volumes (WARNING: deletes data)
	@echo "$(RED)WARNING: This will delete all data from all stacks!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f docker-compose.infrastructure.yml down -v; \
		docker compose -f docker-compose.api.yml down -v; \
		docker compose -f docker-compose.monitor.yml down -v; \
		docker compose -f docker-compose.full.yml down -v; \
		rm -rf data/training_snapshots/*; \
		rm -rf data/monitoring/*; \
		echo "$(GREEN)Cleanup complete!$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

install-local: ## Install dependencies locally (for development)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dependencies installed!$(NC)"

check-health: ## Check health of all services
	@echo "$(BLUE)Checking services health...$(NC)"
	@echo -n "PostgreSQL: "
	@docker exec rakuten_postgres pg_isready -U rakuten_user 2>/dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "MLflow: "
	@curl -s http://localhost:5000/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "Airflow: "
	@curl -s http://localhost:8080/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "API: "
	@curl -s http://localhost:8000/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "Prometheus: "
	@curl -s http://localhost:9090/-/healthy > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "Grafana: "
	@curl -s http://localhost:3000/api/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"

trigger-dag: ## Manually trigger the weekly ML pipeline DAG
	@echo "$(BLUE)Triggering DAG...$(NC)"
	docker exec rakuten_airflow_webserver airflow dags trigger weekly_ml_pipeline
	@echo "$(GREEN)DAG triggered!$(NC)"

list-dags: ## List all Airflow DAGs
	docker exec rakuten_airflow_webserver airflow dags list

dag-errors: ## Show DAG import errors
	docker exec rakuten_airflow_webserver airflow dags list-import-errors

mlflow-experiments: ## List MLflow experiments
	@echo "$(BLUE)MLflow Experiments:$(NC)"
	docker exec rakuten_airflow_webserver mlflow experiments list --tracking-uri http://mlflow:5000

rebuild: ## Rebuild all Docker images
	@echo "$(BLUE)Rebuilding Docker images...$(NC)"
	docker compose -f docker-compose.infrastructure.yml build --no-cache
	docker compose -f docker-compose.api.yml build --no-cache
	@echo "$(GREEN)Rebuild complete!$(NC)"

rebuild-api: ## Rebuild API Docker image
	@echo "$(BLUE)Rebuilding API image...$(NC)"
	docker compose -f docker-compose.api.yml build --no-cache api
	@echo "$(GREEN)API rebuild complete!$(NC)"

# Streamlit
run-streamlit: ## Run Streamlit control room locally
	@echo "$(BLUE)Starting Streamlit...$(NC)"
	@pip list | grep streamlit > /dev/null || (echo "$(YELLOW)Installing streamlit dependencies...$(NC)" && pip install -r requirements-streamlit.txt)
	streamlit run streamlit_app/Home.py

# API Testing
test-api: ## Test API health and prediction endpoints
	@echo "$(BLUE)Testing API...$(NC)"
	@echo -n "Health check: "
	@curl -s http://localhost:8000/health | grep -q "healthy" && echo "$(GREEN)PASS$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo "Metrics endpoint:"
	@curl -s http://localhost:8000/metrics | head -n 10

backup-db: ## Backup PostgreSQL database
	@echo "$(BLUE)Backing up database...$(NC)"
	docker exec -t rakuten_postgres pg_dump -U rakuten_user rakuten_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup complete!$(NC)"

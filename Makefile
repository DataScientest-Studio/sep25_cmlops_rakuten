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

start: ## Start all Docker services
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker compose up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "$(YELLOW)Airflow UI: http://localhost:8080 (admin/admin)$(NC)"
	@echo "$(YELLOW)MLflow UI: http://localhost:5000$(NC)"
	@echo "$(YELLOW)MinIO UI: http://127.0.0.1:9001$(NC)"

stop: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	docker compose down
	@echo "$(GREEN)Services stopped!$(NC)"

restart: stop start ## Restart all services

ps: ## Show running containers
	docker compose ps

logs: ## Show logs from all services
	docker compose logs -f

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
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		rm -rf data/training_snapshots/*; \
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
	@docker exec rakuten_postgres pg_isready -U rakuten_user && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "MLflow: "
	@curl -s http://localhost:5000/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "Airflow: "
	@curl -s http://localhost:8080/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"

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
	docker compose build --no-cache
	@echo "$(GREEN)Rebuild complete!$(NC)"

backup-db: ## Backup PostgreSQL database
	@echo "$(BLUE)Backing up database...$(NC)"
	docker exec -t rakuten_postgres pg_dump -U rakuten_user rakuten_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup complete!$(NC)"

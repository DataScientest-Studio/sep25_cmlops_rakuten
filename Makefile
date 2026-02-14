.PHONY: help setup start stop restart logs clean init-db status load-data generate-dataset test

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Rakuten MLOps - Simplified Makefile$(NC)"
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
	@mkdir -p data/raw data/training_snapshots data/monitoring logs
	@echo "$(GREEN)Setup complete!$(NC)"

start: ## Start all services (Postgres, MLflow, MinIO, API, Monitoring)
	@echo "$(BLUE)Starting all services...$(NC)"
	docker compose up -d
	@echo "$(GREEN)All services started!$(NC)"
	@echo "$(YELLOW)MLflow UI: http://localhost:5000$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/admin)$(NC)"

stop: ## Stop all services
	@echo "$(BLUE)Stopping all services...$(NC)"
	docker compose down
	@echo "$(GREEN)Services stopped!$(NC)"

restart: stop start ## Restart all services

ps: ## Show running containers
	docker compose ps

logs: ## Show logs from all services
	docker compose logs -f

logs-api: ## Show API service logs
	docker compose logs -f api

logs-mlflow: ## Show MLflow logs
	docker logs -f rakuten_mlflow

logs-postgres: ## Show PostgreSQL logs
	docker logs -f rakuten_postgres

init-db: ## Initialize database with 40% of data
	@echo "$(BLUE)Initializing database with 40% of data...$(NC)"
	@echo "$(YELLOW)This will take 2-3 minutes...$(NC)"
	pip install -r requirements.txt
	python src/data/db_init.py
	@echo "$(GREEN)Database initialized!$(NC)"

status: ## Show current data loading status
	@echo "$(BLUE)Checking current status...$(NC)"
	python -c "from src.data.loader import get_current_state; import json; print(json.dumps(get_current_state(), indent=2, default=str))"

load-data: ## Load next increment of data (3%)
	@echo "$(BLUE)Loading next data increment...$(NC)"
	python src/data/loader.py
	@echo "$(GREEN)Data loaded!$(NC)"

generate-dataset: ## Generate balanced dataset
	@echo "$(BLUE)Generating balanced dataset...$(NC)"
	python src/data/dataset_generator.py
	@echo "$(GREEN)Dataset generated!$(NC)"

train-model: ## Train model from database
	@echo "$(BLUE)Training model from database...$(NC)"
	python scripts/train_baseline_model.py
	@echo "$(GREEN)Model trained!$(NC)"

train-model-promote: ## Train model and auto-promote if F1 > 0.70
	@echo "$(BLUE)Training model with auto-promotion...$(NC)"
	python scripts/train_baseline_model.py --auto-promote
	@echo "$(GREEN)Model trained!$(NC)"

shell-postgres: ## Open PostgreSQL shell
	docker exec -it rakuten_postgres psql -U rakuten_user -d rakuten_db

clean: ## Remove all containers and volumes (WARNING: deletes data)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		rm -rf data/training_snapshots/* data/monitoring/*; \
		echo "$(GREEN)Cleanup complete!$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

install-local: ## Install dependencies locally (for development)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dependencies installed!$(NC)"

install-streamlit: ## Install Streamlit dependencies
	@echo "$(BLUE)Installing Streamlit dependencies...$(NC)"
	pip install -r requirements-streamlit.txt
	@echo "$(GREEN)Streamlit dependencies installed!$(NC)"

check-health: ## Check health of all services
	@echo "$(BLUE)Checking services health...$(NC)"
	@echo -n "PostgreSQL: "
	@docker exec rakuten_postgres pg_isready -U rakuten_user 2>/dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "MLflow: "
	@curl -s http://localhost:5000/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "API: "
	@curl -s http://localhost:8000/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "Prometheus: "
	@curl -s http://localhost:9090/-/healthy > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"
	@echo -n "Grafana: "
	@curl -s http://localhost:3000/api/health > /dev/null && echo "$(GREEN)OK$(NC)" || echo "$(RED)FAIL$(NC)"

rebuild: ## Rebuild Docker images
	@echo "$(BLUE)Rebuilding Docker images...$(NC)"
	docker compose build --no-cache
	@echo "$(GREEN)Rebuild complete!$(NC)"

rebuild-api: ## Rebuild API Docker image only
	@echo "$(BLUE)Rebuilding API image...$(NC)"
	docker compose build --no-cache api
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

# Quick demo setup
demo: setup start init-db ## Quick setup for demo (setup + start + init-db)
	@echo "$(GREEN)Demo environment ready!$(NC)"
	@echo "$(YELLOW)Run 'make run-streamlit' to start the control room$(NC)"

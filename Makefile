# Makefile for E-commerce API
# Follows KISS principles with simple, clear commands

.PHONY: help install test lint format clean docker-build docker-run k8s-deploy

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt
	python manage.py migrate

test: ## Run tests with coverage
	coverage run --source='.' manage.py test
	coverage report --fail-under=80
	coverage html

test-unit: ## Run unit tests only
	python manage.py test tests.test_customers tests.test_products tests.test_orders tests.test_notifications

test-integration: ## Run integration tests only
	python manage.py test tests.test_integration

lint: ## Run linting
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	black --check .
	isort --check-only .

format: ## Format code
	black .
	isort .

security: ## Run security checks
	safety check
	bandit -r . -x tests/

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf htmlcov/
	rm -f .coverage

docker-build: ## Build Docker image
	docker build -t ecommerce-api:latest .

docker-run: ## Run with Docker Compose
	docker-compose up -d

docker-stop: ## Stop Docker Compose
	docker-compose down

k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f k8s/

k8s-delete: ## Delete from Kubernetes
	kubectl delete -f k8s/

migrate: ## Run database migrations
	python manage.py makemigrations
	python manage.py migrate

collectstatic: ## Collect static files
	python manage.py collectstatic --noinput

superuser: ## Create superuser
	python manage.py createsuperuser

dev: ## Start development server
	python manage.py runserver

celery: ## Start Celery worker
	celery -A ecommerce worker -l info

celery-beat: ## Start Celery beat scheduler
	celery -A ecommerce beat -l info

#!/bin/bash
# 🚀 Quick Start Script for School Presentation
# Launches the complete Rakuten MLOps project with Streamlit

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       🎓 Rakuten MLOps Project - School Presentation          ║"
echo "║              Quick Start Launch Script                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Check Docker
echo -e "${BLUE}[1/6]${NC} Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Step 2: Check Data Files
echo -e "${BLUE}[2/6]${NC} Checking data files..."
if [ ! -f "data/raw/X_train.csv" ] || [ ! -f "data/raw/Y_train.csv" ]; then
    echo -e "${RED}❌ Training data files not found!${NC}"
    echo "Please ensure X_train.csv and Y_train.csv are in data/raw/"
    exit 1
fi
echo -e "${GREEN}✅ Data files found${NC}"
echo ""

# Step 3: Check if containers are running
echo -e "${BLUE}[3/6]${NC} Checking services..."
CONTAINER_COUNT=$(docker ps --filter "name=rakuten" --format "{{.Names}}" | wc -l)
if [ "$CONTAINER_COUNT" -lt 5 ]; then
    echo -e "${YELLOW}⚠️  Services not fully running. Starting all services...${NC}"
    make start
    echo -e "${YELLOW}⏳ Waiting 30 seconds for services to initialize...${NC}"
    sleep 30
else
    echo -e "${GREEN}✅ Services are running${NC}"
fi
echo ""

# Step 4: Verify services are healthy
echo -e "${BLUE}[4/6]${NC} Verifying service health..."
docker ps --filter "name=rakuten" --format "table {{.Names}}\t{{.Status}}" | head -10
echo ""

# Step 5: Check if database has data
echo -e "${BLUE}[5/6]${NC} Checking database..."
DB_CHECK=$(docker exec rakuten_postgres psql -U rakuten_user -d rakuten_db -tAc "SELECT COUNT(*) FROM products;" 2>/dev/null || echo "0")

if [ "$DB_CHECK" == "0" ]; then
    echo -e "${YELLOW}⚠️  Database is empty. Initializing with 40% of data...${NC}"
    echo -e "${YELLOW}This will take 2-3 minutes...${NC}"
    make init-db
else
    echo -e "${GREEN}✅ Database has $DB_CHECK products${NC}"
fi
echo ""

# Step 6: Launch Streamlit
echo -e "${BLUE}[6/6]${NC} Launching Streamlit Dashboard..."
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     🎉 READY FOR DEMO!                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}📊 Streamlit Dashboard:${NC}  http://localhost:8501"
echo -e "${GREEN}🔄 Airflow UI:${NC}          http://localhost:8080 (admin/admin)"
echo -e "${GREEN}📈 MLflow UI:${NC}           http://localhost:5000"
echo -e "${GREEN}🗄️  MinIO UI:${NC}            http://localhost:9001 (minio_admin/minio_password)"
echo -e "${GREEN}📉 Grafana:${NC}             http://localhost:3000"
echo ""
echo -e "${YELLOW}💡 Quick commands during demo:${NC}"
echo "   make load-data    - Load +3% more data"
echo "   make status       - Check current data percentage"
echo "   make trigger-dag  - Trigger Airflow pipeline"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop Streamlit${NC}"
echo ""

# Navigate to streamlit_app and launch
cd streamlit_app
streamlit run Home.py

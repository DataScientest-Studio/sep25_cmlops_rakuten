# Rakuten MLOps Control Room

A Streamlit-based monitoring and control interface for the Rakuten product classification MLOps pipeline.

## Features

### 🏠 Home Page
- System overview with key metrics
- Docker container status
- Quick links to all pages and external services
- System health summary

### 📊 Database Pipeline
- Current data state (percentage loaded, total rows, last load date)
- Class distribution visualization
- Sample products table with refresh capability
- Recent data loads history

### 🔄 Ingestion & Training
- MLflow experiments overview
- Recent training runs with metrics
- Latest training run details (metrics, parameters)
- Model artifacts browser
- Demo action buttons for pipeline triggers

### 🚀 Model Promotion & Prediction
- Registered models in MLflow Model Registry
- Model promotion interface (stage transitions)
- Interactive prediction simulator
- API health status monitoring

### 📈 Drift & Monitoring
- Grafana dashboards integration
- Prometheus metrics summary
- Inference log statistics and visualizations
- System health overview
- Container uptime and resource monitoring

## Installation

### Prerequisites
- Python 3.9+
- Docker and Docker Compose (for services)
- Running Rakuten MLOps stack

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements-streamlit.txt
   ```

2. **Configure environment:**
   ```bash
   cd streamlit_app
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the application:**
   ```bash
   streamlit run Home.py
   ```

   The app will be available at `http://localhost:8501`

## Configuration

### Environment Variables

Create a `.env` file in the `streamlit_app` directory:

```bash
# PostgreSQL (for local access, use localhost)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rakuten_db
POSTGRES_USER=rakuten_user
POSTGRES_PASSWORD=change_this_password

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# API
API_URL=http://localhost:8000

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000
```

### Running with Docker Services

If your services are running in Docker Compose, make sure:

1. **Port forwarding is enabled** in your `docker-compose.yml`:
   ```yaml
   ports:
     - "5432:5432"  # PostgreSQL
     - "5000:5000"  # MLflow
     - "8000:8000"  # API
     - "9090:9090"  # Prometheus
     - "3000:3000"  # Grafana
   ```

2. **Use `localhost` in .env** when running Streamlit outside Docker

3. **Or run Streamlit inside Docker** and use service names (postgres, mlflow, etc.)

## Usage

### Navigation

The app uses Streamlit's multi-page structure. Navigate between pages using:
- Sidebar menu
- Quick links on the Home page
- Page link buttons

### Key Features

#### Database Monitoring
- View real-time data state
- Visualize class distribution
- Inspect sample products
- Track data load history

#### Experiment Tracking
- Browse MLflow experiments
- View training metrics
- Inspect model parameters
- Download artifacts

#### Model Management
- Promote models between stages
- Test predictions interactively
- Monitor API health

#### System Monitoring
- View Prometheus metrics
- Access Grafana dashboards
- Analyze inference logs
- Check container health

### Refresh Data

Each page has a **🔄 Refresh** button to clear cache and reload data. Data is also cached with TTL (10-30 seconds) for automatic refresh.

## Architecture

```
streamlit_app/
├── Home.py                          # Main entry point
├── pages/                           # Multi-page structure
│   ├── 1_📊_Database_Pipeline.py
│   ├── 2_🔄_Ingestion_Training.py
│   ├── 3_🚀_Model_Promotion.py
│   └── 4_📈_Drift_Monitoring.py
├── components/                      # Reusable components
│   ├── __init__.py
│   └── docker_status.py            # Docker status header
├── managers/                        # Business logic
│   ├── __init__.py
│   └── docker_manager.py           # Docker operations
├── .streamlit/                      # Streamlit config
│   ├── config.toml
│   └── secrets.toml.example
├── .env.example                     # Environment template
└── README.md                        # This file
```

## Troubleshooting

### Cannot Connect to Database
- Ensure PostgreSQL container is running: `docker ps | grep postgres`
- Check port forwarding: `docker-compose ps`
- Verify credentials in `.env`
- Test connection: `psql -h localhost -p 5432 -U rakuten_user -d rakuten_db`

### MLflow Not Available
- Check MLflow container: `docker ps | grep mlflow`
- Verify URL: `curl http://localhost:5000/health`
- Check `MLFLOW_TRACKING_URI` in `.env`

### API Not Responding
- Ensure API container is running: `docker ps | grep api`
- Test health endpoint: `curl http://localhost:8000/health`
- Check logs: `docker logs rakuten_api`

### Docker Status Shows All Red
- Streamlit may not have Docker access
- Install Docker SDK: `pip install docker`
- Check Docker daemon is running: `docker ps`
- Verify Docker socket permissions

## Development

### Adding New Pages

1. Create a new file in `pages/` directory:
   ```python
   # pages/5_🆕_New_Feature.py
   import streamlit as st
   from components.docker_status import render_docker_status
   from managers.docker_manager import docker_manager
   
   st.set_page_config(page_title="New Feature", page_icon="🆕")
   st.title("🆕 New Feature")
   render_docker_status(docker_manager)
   # Your content here
   ```

2. Page will automatically appear in sidebar

### Adding New Components

1. Create component in `components/` directory
2. Import and use in pages:
   ```python
   from components.my_component import render_my_component
   render_my_component(args)
   ```

### Customizing Styles

Edit `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

## Performance Tips

1. **Caching**: Data is cached with TTL. Adjust `ttl` parameter in `@st.cache_data(ttl=seconds)`
2. **Pagination**: Large tables are limited (e.g., top 10, last 5)
3. **Lazy Loading**: Data loaded only when page is accessed
4. **Refresh Control**: Manual refresh clears all caches

## Security Notes

- **Never commit** `.env` files with real credentials
- **Use secrets** for production: `.streamlit/secrets.toml`
- **Limit access** to Streamlit app (authentication add-on)
- **Network isolation** for Docker services

## License

This project is part of the Rakuten MLOps pipeline.

## Support

For issues or questions, refer to the main project documentation.

# Rakuten MLOps - Incremental Data Pipeline

Pipeline de données incrémentales pour le projet Rakuten avec MLflow tracking, PostgreSQL et Airflow orchestration.

## 📋 Architecture

Ce projet implémente une architecture data-centric MLOps avec :

- **PostgreSQL** : Stockage des données avec audit trail complet
- **MLflow** : Versioning des datasets et modèles
- **Airflow** : Orchestration hebdomadaire du pipeline
- **Random Oversampling** : Balancing des classes pour données déséquilibrées

### Pipeline Flow

```
Raw CSV (40% → 100%) → PostgreSQL → Balanced Dataset → MLflow → Model
```

Pour plus de détails, voir [`docs/ARCHITECTURE_PLAN.md`](docs/ARCHITECTURE_PLAN.md)

## 🚀 Quick Start

### Prérequis

- Docker & Docker Compose
- Python 3.11+
- Données brutes dans `data/raw/` (X_train.csv, Y_train.csv, X_test.csv, images/)

### 1. Configuration

Créer un fichier `.env` à partir de l'exemple :

```bash
cp env.example.txt .env
```

Éditer `.env` et configurer les mots de passe :

```bash
POSTGRES_PASSWORD=votre_mot_de_passe
AIRFLOW_PASSWORD=votre_mot_de_passe_airflow
```

### 2. Démarrer l'infrastructure

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier que tous les services sont lancés
docker-compose ps
```

Services disponibles :
- **PostgreSQL** : `localhost:5432`
- **MLflow UI** : http://localhost:5000
- **Airflow UI** : http://localhost:8080 (admin/admin)

### 3. Initialiser la base de données

```bash
# Dans le container Airflow
docker exec -it rakuten_airflow_webserver bash

# Installer les dépendances
pip install -r /requirements.txt

# Initialiser la base avec 40% des données
python /opt/airflow/src/data/db_init.py
```

### 4. Tester le pipeline

```bash
# Charger les 3% suivants
python /opt/airflow/src/data/loader.py

# Générer un dataset balancé
python /opt/airflow/src/data/dataset_generator.py

# Vérifier l'état
python /opt/airflow/src/data/loader.py --status
```

### 5. Activer le DAG Airflow

1. Aller sur http://localhost:8080
2. Se connecter (admin/admin)
3. Activer le DAG `weekly_ml_pipeline`
4. Déclencher manuellement ou attendre l'exécution hebdomadaire

## 📂 Structure du Projet

```
.
├── docker-compose.yml          # Infrastructure Docker
├── env.example.txt             # Variables d'environnement (exemple)
├── requirements.txt            # Dépendances Python
├── docs/
│   └── ARCHITECTURE_PLAN.md    # Plan d'architecture détaillé
├── src/
│   ├── config.py               # Configuration centralisée
│   └── data/
│       ├── schema.sql          # Schéma PostgreSQL
│       ├── db_init.py          # Initialisation DB (40%)
│       ├── loader.py           # Chargement incrémental
│       └── dataset_generator.py # Génération datasets balancés
├── dags/
│   └── weekly_ml_pipeline_dag.py # DAG Airflow
└── data/
    ├── raw/                    # Données brutes (gitignored)
    └── training_snapshots/     # Datasets générés (gitignored)
```

## 🔄 Workflow

### Pipeline Hebdomadaire

Le DAG Airflow s'exécute chaque lundi à minuit et effectue :

1. **Check State** : Vérifier le pourcentage actuel
2. **Load Data** : Charger +3% de données (40% → 43% → 46% ...)
3. **Validate** : Vérifier que les données sont correctement chargées
4. **Generate Dataset** : Créer un dataset balancé via random oversampling
5. **Log to MLflow** : Versionner le dataset dans MLflow
6. **Train Model** : Déclencher l'entraînement (TODO)
7. **Notify** : Envoyer un résumé de l'exécution

Les conteneurs Docker (PostgreSQL, Airflow, MLflow) doivent rester actifs pour que le DAG tourne ; si l'infra est arrêtée ou le Mac/PC passe en veille, le scheduler ne peut pas progresser. En cas d'interruption, relancer `docker-compose up -d`, vérifier que les services sont "Up" puis, en dépannage, déclencher manuellement `weekly_ml_pipeline` depuis l'UI ou avec `docker exec -it rakuten_airflow_webserver airflow dags trigger weekly_ml_pipeline`.

### Commandes Utiles

```bash
# Vérifier l'état actuel
python src/data/loader.py --status

# Voir l'historique des chargements
python src/data/loader.py --history

# Charger manuellement jusqu'à un certain %
python src/data/loader.py --percentage 50

# Générer un dataset balancé
python src/data/dataset_generator.py

# Tester la configuration
python src/config.py
```

## 🗄️ Base de Données

### Tables Principales

- **`products`** : Produits (état actuel)
- **`labels`** : Labels des produits
- **`products_history`** : Audit trail (toutes les modifications)
- **`data_loads`** : Historique des chargements

### Requêtes Utiles

```sql
-- État actuel
SELECT * FROM current_data_state;

-- Distribution des classes
SELECT * FROM class_distribution;

-- Historique des chargements
SELECT batch_name, percentage, total_rows, status, completed_at 
FROM data_loads 
ORDER BY completed_at DESC;

-- Produits ajoutés à une date donnée
SELECT COUNT(*) FROM products_history 
WHERE load_batch_id = (SELECT id FROM data_loads WHERE batch_name = 'week_1');
```

## 📊 MLflow

### Experiments

- **`rakuten_dataset_versioning`** : Datasets générés
- **`rakuten_model_training`** : Modèles entraînés (TODO)

### Accéder à MLflow

```bash
# UI Web
open http://localhost:5000

# Lister les experiments
mlflow experiments list --tracking-uri http://localhost:5000

# Voir les runs d'un experiment
mlflow runs list --experiment-name rakuten_dataset_versioning
```

## 🧪 Tests

```bash
# Tests unitaires (TODO)
pytest tests/

# Tests d'intégration (TODO)
pytest tests/integration/
```

## 🔧 Développement Local

```bash
# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement pour développement local
export POSTGRES_HOST=localhost
export MLFLOW_TRACKING_URI=http://localhost:5000
export DATA_PATH=$(pwd)/data/raw
export ENVIRONMENT=local
```

## 📝 Logs

```bash
# Logs Airflow
docker logs rakuten_airflow_scheduler
docker logs rakuten_airflow_webserver

# Logs PostgreSQL
docker logs rakuten_postgres

# Logs MLflow
docker logs rakuten_mlflow
```

## 🛑 Arrêter les Services

```bash
# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes (attention : perte de données !)
docker-compose down -v
```

## 🐛 Troubleshooting

### Problème : Cannot connect to PostgreSQL

```bash
# Vérifier que le service est lancé
docker-compose ps postgres

# Vérifier les logs
docker logs rakuten_postgres

# Redémarrer le service
docker-compose restart postgres
```

### Problème : Airflow DAG n'apparaît pas

```bash
# Vérifier la syntaxe du DAG
docker exec -it rakuten_airflow_webserver airflow dags list

# Vérifier les erreurs
docker exec -it rakuten_airflow_webserver airflow dags list-import-errors
```

### Problème : MLflow ne track pas les runs

```bash
# Vérifier la connexion à MLflow
curl http://localhost:5000/health

# Vérifier les logs
docker logs rakuten_mlflow
```

## 📚 Documentation Complète

- [Plan d'Architecture](docs/ARCHITECTURE_PLAN.md)
- [Schéma de Base de Données](src/data/schema.sql)
- [Configuration](src/config.py)

## 👥 Contributeurs

Projet réalisé dans le cadre de la formation DataScientest MLOps (septembre 2025).

## 📄 License

Voir [LICENSE](LICENSE)

# Rakuten MLOps - Pipeline Incrémental

Pipeline de données incrémentales : PostgreSQL + MLflow + Airflow  
**Flow:** `Raw CSV (40% → 100%) → PostgreSQL → Balanced Dataset → MLflow → Model`

📖 **Architecture détaillée :** [`docs/ARCHITECTURE_PLAN.md`](docs/ARCHITECTURE_PLAN.md)

---

## 🚀 Démarrage Rapide

### Prérequis
- Docker Desktop en cours d'exécution
- Données dans `data/raw/` (X_train.csv, Y_train.csv, X_test.csv, images/)

### 1. Configuration & Démarrage

```bash
# Configuration initiale
make setup

# Démarrer l'infrastructure (PostgreSQL, MLflow, MinIO, Airflow)
make start

# Vérifier que les services sont actifs
make ps
```

**Services :**
- Airflow UI : http://localhost:8080 (admin/admin)
- MLflow UI : http://localhost:5000
- MinIO UI : http://127.0.0.1:9001 (minio_admin/minio_password)
- PostgreSQL : localhost:5432

### 2. Initialiser les Données (40%)

```bash
make init-db
# ✅ Charge 33,966 produits (40% des données)
```

### 3. Tester le Pipeline

```bash
# Charger +3% supplémentaires (40% → 43%)
make load-data

# Vérifier l'état
make status

# Voir l'historique
make history
```

### 4. Activer le DAG Airflow

1. Ouvrir http://localhost:8080
2. Activer le DAG `weekly_ml_pipeline`
3. Le DAG s'exécute **chaque lundi à minuit** automatiquement

**Note :** Les conteneurs doivent rester actifs. En cas d'arrêt, relancer `make start` puis déclencher manuellement le DAG si nécessaire.

---

## 📋 Commandes Principales

```bash
# Infrastructure
make start              # Démarrer tous les services
make stop               # Arrêter tous les services
make restart            # Redémarrer
make ps                 # Voir les services actifs
make logs               # Voir tous les logs

# Pipeline de données
make init-db            # Initialiser avec 40% des données
make load-data          # Charger +3% supplémentaires
make status             # Voir l'état actuel
make history            # Historique des chargements
make generate-dataset   # Générer un dataset balancé

# Airflow
make trigger-dag        # Déclencher le DAG manuellement
make list-dags          # Lister les DAGs disponibles

# Accès direct
make shell-airflow      # Shell dans le conteneur Airflow
make shell-postgres     # Shell PostgreSQL

# Utilitaires
make check-health       # Vérifier la santé des services
make clean              # Nettoyer (⚠️ supprime les données)
```

## 🔄 Pipeline Hebdomadaire

**DAG Airflow** : s'exécute chaque lundi à minuit (ou manuellement)

1. **Check State** → 2. **Load Data** (+3%) → 3. **Validate** → 4. **Generate Balanced Dataset** → 5. **Log to MLflow** → 6. **Train Model** → 7. **Notify**

**Progression :** 40% → 43% → 46% → ... → 100% (20 semaines)

---

## 🗄️ Base de Données

**Tables :** `products`, `labels`, `products_history` (audit trail), `data_loads` (historique)

```bash
# Accéder à PostgreSQL
make shell-postgres

# Requêtes utiles
SELECT * FROM current_data_state;           # État actuel
SELECT * FROM class_distribution;           # Distribution des classes
SELECT * FROM data_loads ORDER BY completed_at DESC;  # Historique
```

## 📊 MLflow

**UI :** http://localhost:5000  
**Experiments :** `rakuten_dataset_versioning`, `rakuten_model_training`  
**Artifacts :** Stockés dans MinIO (S3-compatible)

---

## 📝 Logs & Debug

```bash
make logs                    # Tous les logs
make logs-airflow           # Logs Airflow scheduler
make logs-postgres          # Logs PostgreSQL
make logs-mlflow            # Logs MLflow
```

## 🐛 Dépannage

| Problème | Solution |
|----------|----------|
| Services ne démarrent pas | `make check-health` puis `make restart` |
| PostgreSQL inaccessible | `make logs-postgres` puis `docker-compose restart postgres` |
| DAG n'apparaît pas | `make dag-errors` pour voir les erreurs d'import |
| Scheduler bloqué | Vérifier que Docker Desktop est actif, relancer `make restart` |

**En cas de problème persistant :**
```bash
make stop && make clean  # ⚠️ Supprime les données
make start && make init-db
```

---

## 📚 Documentation

- [Architecture détaillée](docs/ARCHITECTURE_PLAN.md) - Plan complet du pipeline
- [Rapport de tests](TEST_REPORT_2026-02-10.md) - Tests complets et validés
- [Schéma DB](src/data/schema.sql) - Structure PostgreSQL

**Projet :** Formation DataScientest MLOps (septembre 2025)

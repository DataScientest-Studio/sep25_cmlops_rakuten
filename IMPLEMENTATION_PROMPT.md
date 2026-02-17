# Prompt d'Implémentation - Pipeline MLOps Automatisé

## Contexte du Projet

Je travaille sur un projet MLOps de classification de produits Rakuten. Le repository contient déjà une infrastructure fonctionnelle avec:
- PostgreSQL avec audit trail
- MLflow pour le tracking
- FastAPI pour le serving
- Prometheus + Grafana pour le monitoring
- Interface Streamlit pour le contrôle

**État actuel:** Toutes les opérations (chargement de données, entraînement, promotion) sont manuelles via Streamlit ou scripts.

**Objectif:** Automatiser le pipeline complet selon le workflow suivant:
1. **Chargement hebdomadaire automatique** de +3% des données
2. **Re-entraînement automatique** après chaque chargement
3. **Promotion conditionnelle** du modèle si F1 > seuil (ex: 0.75)
4. **Monitoring continu** du modèle en production
5. **Détection de drift** automatique
6. **Système d'alertes** si drift important
7. **Interface de décision humaine** pour les actions correctives

---

## Tâches à Implémenter

### Phase 1: Orchestration Hebdomadaire (Priorité: HAUTE)

**Objectif:** Mettre en place un scheduler qui déclenche automatiquement le chargement de données chaque semaine.

**Options possibles:**
- Option A: Airflow (plus robuste, UI built-in)
- Option B: Prefect (moderne, plus simple)
- Option C: Cron + Python script (minimaliste)

**Ce que je dois faire:**
1. Choisir la solution d'orchestration adaptée au projet
2. Créer un DAG/Flow/Script qui:
   - S'exécute chaque lundi à 2h du matin (configurable)
   - Appelle le script de chargement de données (+3%)
   - Vérifie que le chargement s'est bien passé
   - Log les résultats
3. Dockeriser la solution d'orchestration
4. L'intégrer au `docker-compose.yml`
5. Ajouter les commandes au `Makefile`

**Fichiers à créer/modifier:**
- `orchestration/scheduler.py` ou `orchestration/dags/weekly_pipeline.py`
- `docker-compose.yml` (ajouter service orchestrateur)
- `Dockerfile.orchestrator` (si nécessaire)
- `Makefile` (nouvelles commandes)

---

### Phase 2: Pipeline d'Entraînement Automatique (Priorité: HAUTE)

**Objectif:** Après chaque chargement de données, déclencher automatiquement un entraînement.

**Ce que je dois faire:**
1. Créer un script `scripts/auto_train.py` qui:
   - Détecte qu'il y a de nouvelles données dans PostgreSQL
   - Génère un dataset balancé automatiquement
   - Lance l'entraînement avec les hyperparamètres par défaut
   - Log tout dans MLflow avec tags spécifiques (ex: `auto_trained=true`)
   - Retourne le run_id du nouveau modèle

2. Intégrer ce script dans le workflow de l'orchestrateur:
   - Task 1: Load data (+3%)
   - Task 2: Auto train (dépend de Task 1)
   - Task 3: Evaluate model (dépend de Task 2)

3. Gérer les erreurs et retry logic

**Fichiers à créer/modifier:**
- `scripts/auto_train.py`
- `src/models/auto_trainer.py` (classe pour l'entraînement automatisé)
- Mise à jour du DAG/Flow d'orchestration

---

### Phase 3: Promotion Automatique Conditionnelle (Priorité: HAUTE)

**Objectif:** Promouvoir automatiquement le nouveau modèle en production si ses performances dépassent un seuil.

**Ce que je dois faire:**
1. Créer un script `scripts/auto_promote.py` qui:
   - Récupère les métriques du nouveau modèle depuis MLflow
   - Compare avec le modèle actuellement en production
   - Décide de la promotion selon les règles:
     - Si F1_nouveau > 0.75 ET F1_nouveau > F1_production → PROMOTE
     - Sinon → ARCHIVE (stage="None" dans MLflow)
   - Log la décision dans MLflow avec justification
   - Si promotion, archive l'ancien modèle en stage "Archived"

2. Ajouter des notifications (optionnel mais recommandé):
   - Email/Slack si promotion effectuée
   - Log dans un fichier de décisions

3. Intégrer dans le workflow orchestré:
   - Task 4: Auto promote (dépend de Task 3)

**Fichiers à créer/modifier:**
- `scripts/auto_promote.py`
- `src/models/promotion_engine.py`
- Configuration des seuils dans `.env` ou `config.yaml`

**Variables de configuration à ajouter:**
```env
AUTO_PROMOTION_ENABLED=true
MIN_F1_THRESHOLD=0.75
PROMOTION_METRIC=weighted_f1
NOTIFICATION_EMAIL=team@example.com
NOTIFICATION_SLACK_WEBHOOK=https://...
```

---

### Phase 4: Monitoring et Détection de Drift (Priorité: MOYENNE)

**Objectif:** Détecter automatiquement quand le modèle en production se dégrade ou que les données dérivent.

**Ce que je dois faire:**
1. Améliorer le système de monitoring existant:
   - Collecter plus de métriques dans `inference_log.csv`
   - Calculer des statistiques sur fenêtres glissantes (7 jours, 30 jours)

2. Créer un module de détection de drift `src/monitoring/drift_monitor.py`:
   - **Data Drift:** Comparer distribution des inputs (longueur texte, vocabulaire)
   - **Prediction Drift:** Analyser distribution des prédictions
   - **Performance Drift:** Simuler avec des données de test
   - Utiliser des tests statistiques (Kolmogorov-Smirnov, PSI)

3. Créer un job périodique (quotidien) qui:
   - Exécute l'analyse de drift
   - Calcule des scores de drift
   - Compare aux seuils configurés
   - Sauvegarde les résultats dans PostgreSQL (table `drift_reports`)

4. Ajouter un dashboard Grafana pour visualiser le drift

**Fichiers à créer/modifier:**
- `src/monitoring/drift_monitor.py`
- `src/monitoring/statistical_tests.py`
- `orchestration/dags/daily_drift_check.py` (nouveau DAG quotidien)
- `src/data/schema.sql` (ajouter table `drift_reports`)
- `grafana/dashboards/drift_monitoring.json`

**Schéma de la table drift_reports:**
```sql
CREATE TABLE drift_reports (
    id SERIAL PRIMARY KEY,
    report_date TIMESTAMP NOT NULL,
    data_drift_score FLOAT,
    prediction_drift_score FLOAT,
    performance_drift_score FLOAT,
    drift_detected BOOLEAN,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### Phase 5: Système d'Alertes (Priorité: MOYENNE)

**Objectif:** Notifier l'équipe quand un drift important est détecté.

**Ce que je dois faire:**
1. Créer un système d'alertes `src/monitoring/alerting.py`:
   - Vérifier les seuils de drift
   - Si drift_score > seuil critique:
     - Envoyer email à l'équipe
     - Poster sur Slack
     - Créer une alerte dans Grafana
     - Logger l'événement

2. Définir les niveaux d'alerte:
   - WARNING: drift_score > 0.1 → Log seulement
   - ALERT: drift_score > 0.2 → Email + Slack
   - CRITICAL: drift_score > 0.3 → Email + Slack + Page on-call

3. Intégrer dans le workflow quotidien de drift detection

**Fichiers à créer/modifier:**
- `src/monitoring/alerting.py`
- `src/monitoring/notification_channels.py` (email, Slack, etc.)
- Configuration dans `.env`

**Variables de configuration:**
```env
ALERT_ENABLED=true
ALERT_EMAIL_FROM=mlops@example.com
ALERT_EMAIL_TO=team@example.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
DRIFT_WARNING_THRESHOLD=0.1
DRIFT_ALERT_THRESHOLD=0.2
DRIFT_CRITICAL_THRESHOLD=0.3
```

---

### Phase 6: Interface de Décision Humaine (Priorité: BASSE)

**Objectif:** Permettre à l'équipe de prendre des décisions quand une alerte est déclenchée.

**Ce que je dois faire:**
1. Ajouter une nouvelle page Streamlit `pages/5_Alerts_Dashboard.py`:
   - Afficher les alertes récentes
   - Détails du drift détecté (graphiques, métriques)
   - Actions disponibles:
     - "Forcer un re-entraînement maintenant"
     - "Investiguer - Ne rien faire"
     - "Ajuster les seuils d'alerte"
     - "Rollback au modèle précédent"
   - Historique des décisions prises

2. Créer une API de contrôle dans FastAPI:
   - `POST /api/trigger-retrain` (force un re-entraînement)
   - `POST /api/rollback-model` (rollback)
   - `GET /api/alerts` (liste des alertes)
   - `POST /api/alerts/{id}/acknowledge` (marquer comme traité)

3. Sauvegarder les actions humaines dans PostgreSQL pour audit

**Fichiers à créer/modifier:**
- `streamlit_app/pages/5_Alerts_Dashboard.py`
- `src/serve/routes.py` (ajouter routes de contrôle)
- `src/data/schema.sql` (table `alert_actions`)

---

### Phase 7: Tests et Documentation (Priorité: MOYENNE)

**Ce que je dois faire:**
1. Écrire des tests pour les nouveaux composants:
   - Tests unitaires pour `auto_train.py`
   - Tests unitaires pour `auto_promote.py`
   - Tests unitaires pour `drift_monitor.py`
   - Tests d'intégration pour le workflow complet

2. Mettre à jour la documentation:
   - `README.md` avec les nouvelles commandes
   - Documentation des DAGs/Flows
   - Guide de réponse aux alertes
   - Runbook pour les incidents

3. Créer des fixtures et données de test

**Fichiers à créer:**
- `tests/test_auto_train.py`
- `tests/test_auto_promote.py`
- `tests/test_drift_monitor.py`
- `tests/test_alerting.py`
- `docs/ALERTING_GUIDE.md`
- `docs/RUNBOOK.md`

---

## Plan d'Implémentation Recommandé

### Sprint 1 (1-2 semaines): Orchestration de Base
- ✅ Phase 1: Orchestration hebdomadaire
- ✅ Phase 2: Pipeline d'entraînement automatique
- 🎯 Livrable: Pipeline qui load data + train automatiquement chaque semaine

### Sprint 2 (1 semaine): Promotion Automatique
- ✅ Phase 3: Promotion conditionnelle
- 🎯 Livrable: Modèles promus automatiquement si performances OK

### Sprint 3 (1-2 semaines): Monitoring et Alertes
- ✅ Phase 4: Détection de drift
- ✅ Phase 5: Système d'alertes
- 🎯 Livrable: Alertes automatiques en cas de drift

### Sprint 4 (1 semaine): Interface et Polish
- ✅ Phase 6: Interface de décision
- ✅ Phase 7: Tests et documentation
- 🎯 Livrable: Système complet et documenté

---

## Questions à Clarifier Avant de Commencer

1. **Orchestration:** Préférence entre Airflow, Prefect ou Cron? (Recommandation: Airflow pour la robustesse)

2. **Notifications:** Avez-vous déjà un Slack workspace? Une adresse email SMTP configurée?

3. **Seuils:** Quels seuils de performance et de drift souhaitez-vous utiliser?
   - F1 minimum pour promotion: 0.75?
   - Drift warning threshold: 0.1?
   - Drift alert threshold: 0.2?

4. **Fréquence:** Confirmation du schedule:
   - Chargement data: Hebdomadaire (lundi 2h)?
   - Drift check: Quotidien (tous les jours 1h)?

5. **Ressources:** Combien de temps de calcul est acceptable pour un entraînement? (pour ajuster les timeouts)

---

## Commandes Make à Ajouter

```makefile
# Orchestration
start-orchestrator    # Démarrer l'orchestrateur
stop-orchestrator     # Arrêter l'orchestrateur
logs-orchestrator     # Voir les logs

# Auto training
trigger-auto-train    # Forcer un entraînement maintenant
trigger-auto-promote  # Forcer une évaluation de promotion

# Monitoring
check-drift           # Exécuter manuellement le drift check
view-alerts           # Afficher les alertes récentes
clear-alerts          # Marquer toutes les alertes comme vues

# Tests
test-pipeline         # Tester le pipeline complet
test-integration      # Tests d'intégration
```

---

## Technologies Suggérées

**Pour l'orchestration:**
- Apache Airflow 2.8+ (robuste, UI complète, large communauté)
- OU Prefect 2.0+ (plus moderne, plus simple)

**Pour les alertes:**
- Python `smtplib` pour les emails
- `slack-sdk` pour Slack
- Grafana Alerting pour les dashboards

**Pour le drift detection:**
- `scipy.stats` pour les tests statistiques
- `alibi-detect` (optionnel, library spécialisée)
- Custom implementation simple

**Pour le stockage:**
- PostgreSQL (déjà en place) pour les rapports et audit
- MLflow (déjà en place) pour les modèles et métriques

---

## Prompt à Utiliser avec l'Assistant

```
Je veux implémenter le pipeline MLOps automatisé décrit dans IMPLEMENTATION_PROMPT.md.

Commençons par la Phase 1: Orchestration Hebdomadaire.

Je souhaite utiliser [Airflow/Prefect/Cron] comme solution d'orchestration.

Aide-moi à:
1. Créer la structure de fichiers nécessaire
2. Écrire le code du DAG/Flow/Script
3. Configurer le service dans docker-compose.yml
4. Tester que ça fonctionne

Procède étape par étape et attends ma validation avant de passer à l'étape suivante.
```

---

## Notes Importantes

- Garder le code simple et maintenable
- Privilégier la robustesse à la complexité
- Logger abondamment pour faciliter le debug
- Penser à la sécurité (pas de secrets en dur, utiliser .env)
- Tester chaque composant individuellement avant l'intégration
- Documenter au fur et à mesure

---

**Statut:** Prêt à commencer l'implémentation
**Date de création:** 2026-02-17
**Dernière mise à jour:** 2026-02-17

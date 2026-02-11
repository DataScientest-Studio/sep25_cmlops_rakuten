# Documentation Index

This directory contains comprehensive documentation for the Rakuten MLOps Control Room project.

## 📚 Documents

### [TARGET_ARCHITECTURE.md](./TARGET_ARCHITECTURE.md)
**Complete system architecture and design**

- System overview diagram
- Component details (FastAPI, Prefect, Streamlit, Monitoring)
- Data flows (training, inference, monitoring)
- Directory structure
- Quick start commands
- Success metrics

**Read this first** to understand the complete vision.

---

### [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
**Phased implementation plan with git checkpoints**

- 8 phases from documentation to integration
- Detailed tasks per phase
- Testing checklists
- Git commit messages for each checkpoint
- Progress tracking
- Troubleshooting guide

**Use this** as your step-by-step implementation guide and to resume work if interrupted.

---

### [ARCHITECTURE_PLAN.md](./ARCHITECTURE_PLAN.md)
**Original incremental data pipeline design** (Phase 1 of project)

- PostgreSQL incremental loading strategy
- Airflow DAG orchestration
- MLflow dataset versioning
- Balanced dataset generation
- Audit trail design

**Historical reference** for the data pipeline foundation.

---

## 🎯 Quick Navigation

**Starting the project?**
1. Read [TARGET_ARCHITECTURE.md](./TARGET_ARCHITECTURE.md) for the big picture
2. Follow [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) phase by phase

**Resuming work?**
1. Check Phase Status in [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
2. Review git log to see last completed phase
3. Continue from next phase

**Understanding the data pipeline?**
1. Read [ARCHITECTURE_PLAN.md](./ARCHITECTURE_PLAN.md) for original design
2. Check database schema in `src/data/schema.sql`
3. Review Airflow DAG in `dags/weekly_ml_pipeline_dag.py`

---

## 📊 Project Status

**Current Phase**: Phase 0 - Documentation ✅  
**Next Phase**: Phase 1 - Docker Compose Refactor  
**Overall Progress**: 1/8 phases (12.5%)

See [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) for detailed progress tracking.

---

**Last Updated**: 2026-02-11

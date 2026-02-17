"""
Rakuten MLOps Pipeline - Home & Presentation

Welcome page with pipeline diagram.
"""
import streamlit as st
from pathlib import Path
import sys
import graphviz

# Load environment variables
sys.path.insert(0, str(Path(__file__).parent))
from utils.env_config import load_env_vars
load_env_vars()

# Page configuration
st.set_page_config(
    page_title="Rakuten MLOps - Pipeline",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Main content
st.markdown('<div class="main-header">Rakuten MLOps Pipeline</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Architecture du Pipeline de Classification de Produits</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Create tabs
st.header("Architecture du Pipeline")

tab1, tab2 = st.tabs(["Architecture Actuelle", "Architecture Idéale"])

with tab1:
    st.subheader("Pipeline Actuel - Containers Docker")
    
    # Current architecture with Docker containers
    diagram_current = graphviz.Digraph()
    diagram_current.attr(rankdir='TB', size='10,12')
    diagram_current.attr('node', shape='box', style='filled,rounded', fontname='Arial', fontsize='12')
    
    # Data Layer
    diagram_current.node('data', 'Données Brutes\n(CSV Files)', fillcolor='#E8F4F8', color='#2E86AB')
    
    # Docker Containers
    diagram_current.node('postgres', '🐳 PostgreSQL\nContainer\n+ Audit Trail', fillcolor='#B8E6F0', color='#2E86AB')
    diagram_current.node('mlflow', '🐳 MLflow\nContainer\nTracking & Registry', fillcolor='#FFC266', color='#FF9800')
    diagram_current.node('minio', '🐳 MinIO\nContainer\nArtifact Storage', fillcolor='#E0E0E0', color='#757575')
    diagram_current.node('api', '🐳 FastAPI\nContainer\nModel Serving', fillcolor='#A5D6A7', color='#4CAF50')
    diagram_current.node('prometheus', '🐳 Prometheus\nContainer\nMetrics', fillcolor='#F8BBD0', color='#E91E63')
    diagram_current.node('grafana', '🐳 Grafana\nContainer\nDashboards', fillcolor='#F48FB1', color='#E91E63')
    
    # Training (local)
    diagram_current.node('training', 'Training Script\n(Local/Manuel)', fillcolor='#FFE5B4', color='#FF9800')
    
    # Edges
    diagram_current.edge('data', 'postgres', label='Load')
    diagram_current.edge('postgres', 'training', label='Query')
    diagram_current.edge('training', 'mlflow', label='Log')
    diagram_current.edge('mlflow', 'minio', label='Store', style='dashed')
    diagram_current.edge('mlflow', 'api', label='Load Model')
    diagram_current.edge('api', 'prometheus', label='Metrics')
    diagram_current.edge('prometheus', 'grafana', label='Visualize')
    
    st.graphviz_chart(diagram_current)

with tab2:
    st.subheader("Pipeline Idéal - Workflow Hebdomadaire Automatisé")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Ideal architecture
        diagram_ideal = graphviz.Digraph()
        diagram_ideal.attr(rankdir='TB', size='10,14')
        diagram_ideal.attr('node', shape='box', style='filled,rounded', fontname='Arial', fontsize='11')
        
        # Data Layer - Weekly increment
        diagram_ideal.node('data_source', 'Source Données\n(+3% hebdo)', fillcolor='#E8F4F8', color='#2E86AB')
        diagram_ideal.node('postgres', 'PostgreSQL\n+ Audit Trail', fillcolor='#B8E6F0', color='#2E86AB')
        diagram_ideal.node('scheduler', 'Scheduler\n(Airflow/Cron)\nHebdomadaire', fillcolor='#FFF3CD', color='#F39C12')
        
        # Auto Training Pipeline
        diagram_ideal.node('auto_load', 'Auto Load\n+3% Data', fillcolor='#D4E6F1', color='#2874A6')
        diagram_ideal.node('auto_train', 'Auto Training\nNouveau Modèle', fillcolor='#FFE5B4', color='#FF9800')
        diagram_ideal.node('mlflow', 'MLflow\nTracking & Registry', fillcolor='#FFC266', color='#FF9800')
        
        # Model Evaluation & Promotion
        diagram_ideal.node('eval', 'Évaluation\nPerformances', fillcolor='#C8E6C9', color='#4CAF50')
        diagram_ideal.node('decision', 'Promotion Auto\nSi F1 > Seuil', fillcolor='#A5D6A7', color='#4CAF50', shape='diamond')
        diagram_ideal.node('production', 'Modèle Production\nFastAPI', fillcolor='#81C784', color='#4CAF50')
        
        # Monitoring & Drift Detection
        diagram_ideal.node('monitoring', 'Monitoring\nProduction', fillcolor='#F8BBD0', color='#E91E63')
        diagram_ideal.node('drift_detect', 'Détection Drift\nAutomatique', fillcolor='#F48FB1', color='#E91E63')
        diagram_ideal.node('alert', 'Alarme\nDrift Important', fillcolor='#F06292', color='#C2185B', shape='box')
        diagram_ideal.node('human', 'Décision Humaine\nRe-train / Investigate', fillcolor='#FFE082', color='#F57C00')
        
        # Storage
        diagram_ideal.node('storage', 'Cloud Storage\nArtifacts', fillcolor='#E0E0E0', color='#757575')
        
        # Weekly cycle edges
        diagram_ideal.edge('scheduler', 'auto_load', label='Trigger\nhebdo')
        diagram_ideal.edge('data_source', 'postgres', label='+3%')
        diagram_ideal.edge('auto_load', 'postgres', label='Load')
        diagram_ideal.edge('auto_load', 'auto_train', label='Trigger')
        
        # Training flow
        diagram_ideal.edge('postgres', 'auto_train', label='Data')
        diagram_ideal.edge('auto_train', 'mlflow', label='Log\nrun')
        diagram_ideal.edge('mlflow', 'storage', label='Artifacts', style='dashed')
        diagram_ideal.edge('mlflow', 'eval', label='Metrics')
        
        # Promotion decision
        diagram_ideal.edge('eval', 'decision', label='Comparer')
        diagram_ideal.edge('decision', 'production', label='OUI:\nPromote', color='green')
        diagram_ideal.edge('decision', 'mlflow', label='NON:\nArchive', color='red', style='dashed')
        
        # Production monitoring
        diagram_ideal.edge('production', 'monitoring', label='Logs\n& Metrics')
        diagram_ideal.edge('monitoring', 'drift_detect', label='Analyze')
        diagram_ideal.edge('drift_detect', 'alert', label='Drift > Seuil', color='red')
        diagram_ideal.edge('alert', 'human', label='Notify')
        diagram_ideal.edge('human', 'scheduler', label='Action:\nForce retrain', style='dashed')
        
        st.graphviz_chart(diagram_ideal)
    
    with col2:
        st.markdown("### Fonctionnement")
        
        st.markdown("""
        **1. Chargement Hebdomadaire (+3%)**
        
        Chaque semaine, un scheduler (Airflow/cron) déclenche:
        - Chargement automatique de 3% de nouvelles données
        - Mise à jour de PostgreSQL avec audit trail
        - Progression de 40% → 100% en ~20 semaines
        
        ---
        
        **2. Re-entraînement Automatique**
        
        Immédiatement après le chargement:
        - Nouveau modèle entraîné automatiquement
        - Même architecture (TF-IDF + LogReg)
        - Toutes les métriques loggées dans MLflow
        - Artifacts sauvegardés dans cloud storage
        
        ---
        
        **3. Promotion Conditionnelle**
        
        Le nouveau modèle est évalué:
        - Comparaison des métriques (F1, accuracy)
        - Si F1 > seuil (ex: 0.75) → Promotion automatique
        - Si F1 < seuil → Archive dans MLflow (pas de promotion)
        
        Cela évite de dégrader la production avec des modèles moins performants.
        
        ---
        
        **4. Monitoring en Production**
        
        Le modèle en production est surveillé:
        - Logs d'inférence (predictions, confidences)
        - Métriques de performance
        - Distribution des prédictions
        - Latence et errors
        
        ---
        
        **5. Détection de Drift**
        
        Analyse automatique du drift:
        - **Drift de données**: Distribution des inputs change
        - **Drift de modèle**: Performances se dégradent
        - Calcul de scores de drift (KS test, PSI, etc.)
        
        ---
        
        **6. Alarme & Décision Humaine**
        
        Si drift important détecté (> seuil):
        - Alerte envoyée à l'équipe (email, Slack)
        - Dashboard de monitoring mis à jour
        - **Décision humaine requise:**
          - Investiguer la cause du drift
          - Forcer un re-entraînement si nécessaire
          - Ajuster les hyperparamètres
          - Ou attendre le prochain cycle hebdo
        
        ---
        
        **Avantages:**
        - Automatisation du cycle hebdomadaire
        - Contrôle qualité avant production
        - Surveillance continue du modèle
        - Intervention humaine seulement si nécessaire
        - Traçabilité complète via MLflow
        """)
        
        st.success("**Cycle complet:** Load → Train → Eval → Deploy (si OK) → Monitor → Alert (si drift)")
    
    st.markdown("<br>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666;">
        <small>DataScientest MLOps Certification - September 2025</small>
    </div>
    """, unsafe_allow_html=True)

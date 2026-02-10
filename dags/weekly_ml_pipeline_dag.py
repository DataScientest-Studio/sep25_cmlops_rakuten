"""
Weekly ML Pipeline DAG
Orchestrates the complete ML pipeline: incremental data loading, dataset generation, and model training
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/opt/airflow')

# Default arguments for the DAG
default_args = {
    'owner': 'rakuten_mlops',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def check_current_state(**context):
    """Check current data loading state and determine if we need to load more data"""
    from src.data.loader import get_current_state, calculate_next_percentage
    from src.config import PIPELINE_CONFIG
    
    state = get_current_state()
    current_pct = state['current_percentage']
    next_pct = calculate_next_percentage(current_pct)
    max_pct = PIPELINE_CONFIG['max_percentage']
    
    print(f"📊 Current State:")
    print(f"  - Current percentage: {current_pct}%")
    print(f"  - Next percentage: {next_pct}%")
    print(f"  - Max percentage: {max_pct}%")
    
    # Push to XCom for downstream tasks
    context['ti'].xcom_push(key='current_percentage', value=current_pct)
    context['ti'].xcom_push(key='next_percentage', value=next_pct)
    context['ti'].xcom_push(key='should_load', value=current_pct < max_pct)
    
    if current_pct >= max_pct:
        print(f"✅ Already at maximum ({max_pct}%), no more data to load")
        return 'skip_load'
    else:
        print(f"➡️  Will load data from {current_pct}% to {next_pct}%")
        return 'load_data'


def load_incremental_data(**context):
    """Load next increment of data into PostgreSQL"""
    from src.data.loader import load_incremental_data
    
    # Get next percentage from XCom
    next_pct = context['ti'].xcom_pull(key='next_percentage', task_ids='check_current_state')
    
    print(f"Loading data up to {next_pct}%...")
    
    success = load_incremental_data(target_percentage=next_pct)
    
    if not success:
        raise Exception("Failed to load incremental data")
    
    print(f"✅ Data loaded successfully to {next_pct}%")


def validate_data_load(**context):
    """Validate that data was loaded correctly"""
    import psycopg2
    from src.config import POSTGRES_CONFIG
    
    next_pct = context['ti'].xcom_pull(key='next_percentage', task_ids='check_current_state')
    
    print(f"Validating data load for {next_pct}%...")
    
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Check products count
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        # Check labels count
        cursor.execute("SELECT COUNT(*) FROM labels")
        labels_count = cursor.fetchone()[0]
        
        # Check latest load
        cursor.execute("""
            SELECT percentage, status, total_rows
            FROM data_loads
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            loaded_pct, status, total_rows = result
            
            print(f"📊 Validation Results:")
            print(f"  - Products in DB: {products_count}")
            print(f"  - Labels in DB: {labels_count}")
            print(f"  - Latest load: {loaded_pct}% ({total_rows} rows)")
            
            if products_count != labels_count:
                raise Exception(f"Mismatch: {products_count} products but {labels_count} labels")
            
            if abs(loaded_pct - next_pct) > 0.1:
                raise Exception(f"Expected {next_pct}% but got {loaded_pct}%")
            
            print("✅ Validation passed!")
        else:
            raise Exception("No completed data loads found")
    
    finally:
        cursor.close()
        conn.close()


def generate_balanced_dataset(**context):
    """Generate balanced dataset from current database state"""
    from src.data.dataset_generator import generate_balanced_dataset, save_and_log_dataset
    from src.config import PIPELINE_CONFIG
    
    print("Generating balanced dataset...")
    
    df_balanced, week_number, metadata = generate_balanced_dataset(
        strategy=PIPELINE_CONFIG['balancing_strategy']
    )
    
    if df_balanced is None:
        raise Exception("Failed to generate balanced dataset")
    
    print(f"✅ Generated balanced dataset for week {week_number}")
    print(f"  - Original size: {metadata['original_size']}")
    print(f"  - Balanced size: {metadata['balanced_size']}")
    
    # Save and log to MLflow
    run_id = save_and_log_dataset(df_balanced, week_number, metadata)
    
    # Push to XCom for downstream tasks
    context['ti'].xcom_push(key='dataset_run_id', value=run_id)
    context['ti'].xcom_push(key='week_number', value=week_number)
    
    print(f"✅ Dataset logged to MLflow (run_id: {run_id})")


def trigger_model_training(**context):
    """Trigger model training with the newly generated dataset"""
    dataset_run_id = context['ti'].xcom_pull(key='dataset_run_id', task_ids='generate_balanced_dataset')
    week_number = context['ti'].xcom_pull(key='week_number', task_ids='generate_balanced_dataset')
    
    print(f"🚀 Triggering model training for week {week_number}")
    print(f"   Dataset run_id: {dataset_run_id}")
    
    # TODO: Implement model training
    # For now, just log that we would trigger training
    print("⚠️  Model training not yet implemented")
    print("   This would normally call src/models/train.py")
    
    # In future implementation:
    # from src.models.train import train_model
    # model_run_id = train_model(dataset_run_id=dataset_run_id, week_number=week_number)
    # context['ti'].xcom_push(key='model_run_id', value=model_run_id)


def send_notification(**context):
    """Send notification about pipeline completion"""
    current_pct = context['ti'].xcom_pull(key='current_percentage', task_ids='check_current_state')
    next_pct = context['ti'].xcom_pull(key='next_percentage', task_ids='check_current_state')
    should_load = context['ti'].xcom_pull(key='should_load', task_ids='check_current_state')
    
    print("\n" + "="*80)
    print("📬 PIPELINE EXECUTION SUMMARY")
    print("="*80)
    print(f"Execution Date: {context['ds']}")
    print(f"Previous Percentage: {current_pct}%")
    
    if should_load:
        week_number = context['ti'].xcom_pull(key='week_number', task_ids='generate_balanced_dataset')
        dataset_run_id = context['ti'].xcom_pull(key='dataset_run_id', task_ids='generate_balanced_dataset')
        
        print(f"New Percentage: {next_pct}%")
        print(f"Week Number: {week_number}")
        print(f"Dataset MLflow Run ID: {dataset_run_id}")
        print("Status: ✅ SUCCESS - Data loaded and dataset generated")
    else:
        print(f"Status: ℹ️  SKIPPED - Already at maximum ({current_pct}%)")
    
    print("="*80)


# Define the DAG
with DAG(
    dag_id='weekly_ml_pipeline',
    default_args=default_args,
    description='Weekly ML Pipeline: Incremental Data Loading + Dataset Generation + Model Training',
    schedule_interval='0 0 * * 1',  # Every Monday at midnight (or from env var)
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'rakuten', 'incremental', 'weekly'],
) as dag:
    
    # Task 1: Check current state
    check_state = PythonOperator(
        task_id='check_current_state',
        python_callable=check_current_state,
        provide_context=True,
    )
    
    # Task 2: Load incremental data
    load_data = PythonOperator(
        task_id='load_incremental_data',
        python_callable=load_incremental_data,
        provide_context=True,
    )
    
    # Task 3: Validate data load
    validate_load = PythonOperator(
        task_id='validate_data_load',
        python_callable=validate_data_load,
        provide_context=True,
    )
    
    # Task 4: Generate balanced dataset
    generate_dataset = PythonOperator(
        task_id='generate_balanced_dataset',
        python_callable=generate_balanced_dataset,
        provide_context=True,
    )
    
    # Task 5: Trigger model training
    train_model = PythonOperator(
        task_id='trigger_model_training',
        python_callable=trigger_model_training,
        provide_context=True,
    )
    
    # Task 6: Send notification
    notify = PythonOperator(
        task_id='send_notification',
        python_callable=send_notification,
        provide_context=True,
    )
    
    # Define task dependencies
    check_state >> load_data >> validate_load >> generate_dataset >> train_model >> notify

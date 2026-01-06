"""
Balanced Dataset Generator
Generates balanced training datasets from PostgreSQL and logs them to MLflow
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import psycopg2
import mlflow
import logging
from collections import Counter
from imblearn.over_sampling import RandomOverSampler
import matplotlib.pyplot as plt
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import (
    POSTGRES_CONFIG,
    MLFLOW_CONFIG,
    PIPELINE_CONFIG,
    TRAINING_SNAPSHOTS_PATH,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_current_data_from_db():
    """
    Extract current data from PostgreSQL database
    
    Returns:
        pd.DataFrame: Current dataset with features and labels
    """
    logger.info("Extracting data from PostgreSQL...")
    
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    
    try:
        query = """
        SELECT 
            p.productid,
            p.designation,
            p.description,
            p.imageid,
            p.image_path,
            l.prdtypecode
        FROM products p
        JOIN labels l ON p.productid = l.productid
        ORDER BY p.created_at
        """
        
        df = pd.read_sql_query(query, conn)
        logger.info(f"Extracted {len(df)} rows from database")
        
        return df
    
    finally:
        conn.close()


def get_current_percentage():
    """Get current data loading percentage"""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT percentage, batch_name
            FROM data_loads
            WHERE status = 'completed'
            ORDER BY percentage DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            return float(result[0]), result[1]
        else:
            return 0, 'initial'
    
    finally:
        cursor.close()
        conn.close()


def analyze_class_distribution(df: pd.DataFrame, title: str = "Class Distribution"):
    """
    Analyze and visualize class distribution
    
    Args:
        df: DataFrame with 'prdtypecode' column
        title: Plot title
        
    Returns:
        dict: Class distribution statistics
    """
    class_counts = Counter(df['prdtypecode'])
    
    logger.info(f"\n📊 {title}:")
    logger.info(f"  - Total samples: {len(df)}")
    logger.info(f"  - Number of classes: {len(class_counts)}")
    logger.info(f"  - Min class size: {min(class_counts.values())}")
    logger.info(f"  - Max class size: {max(class_counts.values())}")
    logger.info(f"  - Mean class size: {sum(class_counts.values()) / len(class_counts):.1f}")
    
    # Calculate imbalance ratio
    max_count = max(class_counts.values())
    min_count = min(class_counts.values())
    imbalance_ratio = max_count / min_count if min_count > 0 else float('inf')
    logger.info(f"  - Imbalance ratio: {imbalance_ratio:.2f}")
    
    return {
        'total_samples': len(df),
        'num_classes': len(class_counts),
        'min_class_size': min(class_counts.values()),
        'max_class_size': max(class_counts.values()),
        'mean_class_size': sum(class_counts.values()) / len(class_counts),
        'imbalance_ratio': imbalance_ratio,
        'class_counts': dict(class_counts)
    }


def plot_class_distribution(class_counts: dict, title: str, output_path: Path):
    """
    Create visualization of class distribution
    
    Args:
        class_counts: Dictionary of class counts
        title: Plot title
        output_path: Path to save plot
    """
    plt.figure(figsize=(12, 6))
    
    classes = sorted(class_counts.keys())
    counts = [class_counts[c] for c in classes]
    
    plt.bar(range(len(classes)), counts)
    plt.xlabel('Product Type Code')
    plt.ylabel('Count')
    plt.title(title)
    plt.xticks(range(len(classes)), classes, rotation=45)
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved class distribution plot: {output_path}")


def generate_balanced_dataset(strategy: str = 'random_oversampling'):
    """
    Generate balanced dataset using specified strategy
    
    Args:
        strategy: Balancing strategy (currently only 'random_oversampling')
        
    Returns:
        tuple: (balanced_df, week_number, metadata)
    """
    # Get current data
    df = get_current_data_from_db()
    
    if len(df) == 0:
        logger.error("No data in database")
        return None, None, None
    
    # Get current percentage and week
    percentage, batch_name = get_current_percentage()
    week_number = int((percentage - PIPELINE_CONFIG['initial_percentage']) / PIPELINE_CONFIG['increment_percentage']) + 1
    
    logger.info(f"Generating balanced dataset for week {week_number} ({percentage}% data)")
    
    # Analyze original distribution
    original_stats = analyze_class_distribution(df, "Original Distribution")
    
    # Prepare features and target
    X = df[['productid', 'designation', 'description', 'imageid', 'image_path']]
    y = df['prdtypecode']
    
    # Apply random oversampling
    if strategy == 'random_oversampling':
        logger.info("Applying random oversampling...")
        
        ros = RandomOverSampler(random_state=PIPELINE_CONFIG['random_seed'])
        X_resampled, y_resampled = ros.fit_resample(X, y)
        
        # Reconstruct DataFrame
        df_balanced = X_resampled.copy()
        df_balanced['prdtypecode'] = y_resampled
        
        logger.info(f"Original size: {len(df)} → Balanced size: {len(df_balanced)}")
    else:
        logger.error(f"Unknown balancing strategy: {strategy}")
        return None, None, None
    
    # Analyze balanced distribution
    balanced_stats = analyze_class_distribution(df_balanced, "Balanced Distribution")
    
    # Verify balance
    class_counts_balanced = Counter(df_balanced['prdtypecode'])
    unique_counts = set(class_counts_balanced.values())
    
    if len(unique_counts) == 1:
        logger.info("✅ Perfect balance achieved!")
    else:
        logger.warning(f"⚠️  Slight imbalance detected: {unique_counts}")
    
    # Metadata
    metadata = {
        'week_number': week_number,
        'percentage': percentage,
        'batch_name': batch_name,
        'strategy': strategy,
        'original_size': len(df),
        'balanced_size': len(df_balanced),
        'original_stats': original_stats,
        'balanced_stats': balanced_stats,
        'timestamp': datetime.now().isoformat()
    }
    
    return df_balanced, week_number, metadata


def save_and_log_dataset(df_balanced: pd.DataFrame, week_number: int, metadata: dict):
    """
    Save dataset as parquet and log to MLflow
    
    Args:
        df_balanced: Balanced dataset
        week_number: Week number
        metadata: Dataset metadata
    """
    # Create output directory
    TRAINING_SNAPSHOTS_PATH.mkdir(parents=True, exist_ok=True)
    
    # Save as parquet
    output_file = TRAINING_SNAPSHOTS_PATH / f"train_week_{week_number}.parquet"
    df_balanced.to_parquet(output_file, index=False)
    logger.info(f"Saved dataset to: {output_file}")
    
    # Set MLflow tracking URI
    mlflow.set_tracking_uri(MLFLOW_CONFIG['tracking_uri'])
    
    # Set or create experiment
    experiment_name = MLFLOW_CONFIG['experiment_dataset']
    experiment = mlflow.get_experiment_by_name(experiment_name)
    
    if experiment is None:
        experiment_id = mlflow.create_experiment(experiment_name)
        logger.info(f"Created MLflow experiment: {experiment_name}")
    else:
        experiment_id = experiment.experiment_id
    
    # Start MLflow run
    with mlflow.start_run(experiment_id=experiment_id, run_name=f"week_{week_number}_dataset"):
        # Log parameters
        mlflow.log_param("week_number", week_number)
        mlflow.log_param("percentage", metadata['percentage'])
        mlflow.log_param("balancing_strategy", metadata['strategy'])
        mlflow.log_param("original_size", metadata['original_size'])
        mlflow.log_param("balanced_size", metadata['balanced_size'])
        mlflow.log_param("random_seed", PIPELINE_CONFIG['random_seed'])
        
        # Log metrics
        mlflow.log_metric("num_classes", metadata['balanced_stats']['num_classes'])
        mlflow.log_metric("total_samples", metadata['balanced_stats']['total_samples'])
        mlflow.log_metric("imbalance_ratio_before", metadata['original_stats']['imbalance_ratio'])
        mlflow.log_metric("imbalance_ratio_after", metadata['balanced_stats']['imbalance_ratio'])
        
        # Log class counts as metrics
        for class_code, count in metadata['balanced_stats']['class_counts'].items():
            mlflow.log_metric(f"class_{class_code}_count", count)
        
        # Create and log class distribution plots
        plot_before_path = TRAINING_SNAPSHOTS_PATH / f"week_{week_number}_distribution_before.png"
        plot_after_path = TRAINING_SNAPSHOTS_PATH / f"week_{week_number}_distribution_after.png"
        
        plot_class_distribution(
            metadata['original_stats']['class_counts'],
            f"Week {week_number} - Before Balancing",
            plot_before_path
        )
        
        plot_class_distribution(
            metadata['balanced_stats']['class_counts'],
            f"Week {week_number} - After Balancing",
            plot_after_path
        )
        
        mlflow.log_artifact(str(plot_before_path))
        mlflow.log_artifact(str(plot_after_path))
        
        # Save and log metadata as JSON
        metadata_file = TRAINING_SNAPSHOTS_PATH / f"week_{week_number}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        mlflow.log_artifact(str(metadata_file))
        
        # Log dataset parquet file
        mlflow.log_artifact(str(output_file))
        
        # Log tags
        mlflow.set_tag("dataset_type", "training")
        mlflow.set_tag("week", week_number)
        mlflow.set_tag("percentage", f"{metadata['percentage']}%")
        
        run_id = mlflow.active_run().info.run_id
        logger.info(f"✅ Logged dataset to MLflow (run_id: {run_id})")
        
        return run_id


def main():
    """Main function"""
    logger.info("=== Balanced Dataset Generator ===\n")
    
    try:
        # Generate balanced dataset
        df_balanced, week_number, metadata = generate_balanced_dataset(
            strategy=PIPELINE_CONFIG['balancing_strategy']
        )
        
        if df_balanced is None:
            logger.error("Failed to generate balanced dataset")
            return False
        
        # Save and log to MLflow
        run_id = save_and_log_dataset(df_balanced, week_number, metadata)
        
        logger.info("\n✅ Dataset generation and logging completed successfully!")
        logger.info(f"   Run ID: {run_id}")
        logger.info(f"   Week: {week_number}")
        logger.info(f"   Dataset size: {len(df_balanced)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating dataset: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

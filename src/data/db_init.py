"""
Database Initialization Script
Initializes the PostgreSQL database and loads initial 40% of training data
"""
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import (
    POSTGRES_CONFIG,
    DATABASE_URL,
    DATA_FILES,
    PIPELINE_CONFIG,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_databases():
    """Create necessary databases if they don't exist"""
    logger.info("Creating databases...")
    
    # Connect to postgres default database
    conn = psycopg2.connect(
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port'],
        user=POSTGRES_CONFIG['user'],
        password=POSTGRES_CONFIG['password'],
        database='postgres'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Create databases
    databases = [
        POSTGRES_CONFIG['database'],
        'mlflow_db',
        'airflow_db'
    ]
    
    for db_name in databases:
        try:
            cursor.execute(f"CREATE DATABASE {db_name};")
            logger.info(f"Created database: {db_name}")
        except psycopg2.errors.DuplicateDatabase:
            logger.info(f"Database {db_name} already exists")
    
    cursor.close()
    conn.close()


def initialize_schema():
    """Initialize database schema using schema.sql"""
    logger.info("Initializing database schema...")
    
    schema_file = Path(__file__).parent / "schema.sql"
    
    if not schema_file.exists():
        logger.error(f"Schema file not found: {schema_file}")
        return False
    
    # Read schema file
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Execute schema (skip CREATE DATABASE commands as we already did that)
    engine = create_engine(DATABASE_URL)
    
    # Split by statements and execute (excluding CREATE DATABASE statements)
    statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
    
    with engine.connect() as conn:
        for statement in statements:
            # Skip CREATE DATABASE and \c commands
            if statement.startswith('CREATE DATABASE') or statement.startswith('\\c') or statement.startswith('\\d'):
                continue
            
            if statement:
                try:
                    conn.execute(text(statement))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Error executing statement (may be normal): {e}")
    
    logger.info("Schema initialized successfully")
    return True


def load_initial_data(percentage: float = None):
    """
    Load initial percentage of training data into database
    
    Args:
        percentage: Percentage of data to load (default: from config)
    """
    if percentage is None:
        percentage = PIPELINE_CONFIG['initial_percentage']
    
    logger.info(f"Loading initial {percentage}% of training data...")
    
    # Check if data files exist
    if not DATA_FILES['x_train'].exists():
        logger.error(f"Training data not found: {DATA_FILES['x_train']}")
        logger.info("Please ensure data files are in the data/raw/ directory")
        return False
    
    # Read data files
    logger.info("Reading CSV files...")
    x_train = pd.read_csv(DATA_FILES['x_train'])
    y_train = pd.read_csv(DATA_FILES['y_train'])
    
    # Merge datasets
    df = x_train.merge(y_train, on='productid', how='inner')
    
    total_rows = len(df)
    target_rows = int(total_rows * percentage / 100)
    
    logger.info(f"Total available rows: {total_rows}")
    logger.info(f"Target rows ({percentage}%): {target_rows}")
    
    # Deterministic sampling
    df_sample = df.sample(
        n=target_rows,
        random_state=PIPELINE_CONFIG['random_seed']
    ).reset_index(drop=True)
    
    # Add image paths
    images_dir = DATA_FILES['images_dir']
    df_sample['image_path'] = df_sample['imageid'].apply(
        lambda img_id: f"images/image_train/image_{img_id}_product_{df_sample[df_sample['imageid'] == img_id]['productid'].iloc[0] if len(df_sample[df_sample['imageid'] == img_id]) > 0 else 0}.jpg"
    )
    
    # Connect to database
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Start batch tracking
        cursor.execute("""
            INSERT INTO data_loads (batch_name, percentage, total_rows, status, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            f'initial_{percentage}pct',
            percentage,
            target_rows,
            'running',
            {'type': 'initial_load'}
        ))
        batch_id = cursor.fetchone()[0]
        conn.commit()
        
        logger.info(f"Created batch record with ID: {batch_id}")
        
        # Insert products
        logger.info("Inserting products...")
        products_data = [
            (
                row['designation'],
                row['description'],
                row['productid'],
                row['imageid'],
                row['image_path']
            )
            for _, row in df_sample.iterrows()
        ]
        
        execute_values(
            cursor,
            """
            INSERT INTO products (designation, description, productid, imageid, image_path)
            VALUES %s
            ON CONFLICT (productid) DO NOTHING
            """,
            products_data
        )
        
        logger.info(f"Inserted {len(products_data)} products")
        
        # Insert labels
        logger.info("Inserting labels...")
        labels_data = [
            (row['productid'], row['prdtypecode'])
            for _, row in df_sample.iterrows()
        ]
        
        execute_values(
            cursor,
            """
            INSERT INTO labels (productid, prdtypecode)
            VALUES %s
            ON CONFLICT (productid) DO NOTHING
            """,
            labels_data
        )
        
        logger.info(f"Inserted {len(labels_data)} labels")
        
        # Complete batch
        cursor.execute("""
            UPDATE data_loads
            SET status = 'completed', completed_at = NOW()
            WHERE id = %s
        """, (batch_id,))
        
        conn.commit()
        
        logger.info("✅ Initial data load completed successfully!")
        
        # Print summary
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT prdtypecode) FROM labels")
        classes_count = cursor.fetchone()[0]
        
        logger.info(f"\n📊 Database Summary:")
        logger.info(f"  - Products: {products_count}")
        logger.info(f"  - Classes: {classes_count}")
        logger.info(f"  - Percentage loaded: {percentage}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        conn.rollback()
        # Mark batch as failed
        cursor.execute("""
            UPDATE data_loads
            SET status = 'failed'
            WHERE batch_name = %s
        """, (f'initial_{percentage}pct',))
        conn.commit()
        return False
        
    finally:
        cursor.close()
        conn.close()


def main():
    """Main initialization function"""
    logger.info("=== Rakuten MLOps Database Initialization ===\n")
    
    try:
        # Step 1: Create databases
        create_databases()
        
        # Step 2: Initialize schema
        if not initialize_schema():
            logger.error("Failed to initialize schema")
            return False
        
        # Step 3: Load initial data
        if not load_initial_data():
            logger.error("Failed to load initial data")
            return False
        
        logger.info("\n✅ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

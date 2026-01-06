"""
Incremental Data Loader
Loads data incrementally into PostgreSQL database following cumulative strategy
"""
import sys
from pathlib import Path
from datetime import datetime
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


def get_current_state():
    """
    Get current data loading state from database
    
    Returns:
        dict: Current state with percentage, total_rows, last_load_date
    """
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT percentage, total_rows, completed_at
            FROM data_loads
            WHERE status = 'completed'
            ORDER BY percentage DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            return {
                'current_percentage': float(result[0]),
                'total_rows': result[1],
                'last_load_date': result[2]
            }
        else:
            return {
                'current_percentage': 0,
                'total_rows': 0,
                'last_load_date': None
            }
    
    finally:
        cursor.close()
        conn.close()


def calculate_next_percentage(current_percentage: float) -> float:
    """
    Calculate next percentage to load
    
    Args:
        current_percentage: Current percentage loaded
        
    Returns:
        Next percentage to load
    """
    next_pct = current_percentage + PIPELINE_CONFIG['increment_percentage']
    return min(next_pct, PIPELINE_CONFIG['max_percentage'])


def load_incremental_data(target_percentage: float = None):
    """
    Load data incrementally up to target percentage (cumulative strategy)
    
    Args:
        target_percentage: Target percentage to reach (if None, uses next increment)
        
    Returns:
        bool: Success status
    """
    # Get current state
    state = get_current_state()
    current_pct = state['current_percentage']
    
    logger.info(f"Current state: {current_pct}% loaded")
    
    # Determine target percentage
    if target_percentage is None:
        target_percentage = calculate_next_percentage(current_pct)
    
    # Check if already at target
    if current_pct >= target_percentage:
        logger.info(f"Already at {current_pct}%, target is {target_percentage}%")
        return True
    
    # Check if at max
    if current_pct >= PIPELINE_CONFIG['max_percentage']:
        logger.info(f"Already at maximum ({PIPELINE_CONFIG['max_percentage']}%)")
        return True
    
    logger.info(f"Loading data from {current_pct}% to {target_percentage}%...")
    
    # Check if data files exist
    if not DATA_FILES['x_train'].exists():
        logger.error(f"Training data not found: {DATA_FILES['x_train']}")
        return False
    
    # Read data files
    logger.info("Reading CSV files...")
    x_train = pd.read_csv(DATA_FILES['x_train'])
    y_train = pd.read_csv(DATA_FILES['y_train'])
    
    # Merge datasets
    df = x_train.merge(y_train, on='productid', how='inner')
    
    total_rows = len(df)
    target_rows = int(total_rows * target_percentage / 100)
    
    logger.info(f"Total available rows: {total_rows}")
    logger.info(f"Target rows ({target_percentage}%): {target_rows}")
    
    # Deterministic sampling (cumulative: always sample from full dataset)
    df_sample = df.sample(
        n=target_rows,
        random_state=PIPELINE_CONFIG['random_seed']
    ).reset_index(drop=True)
    
    # Add image paths
    df_sample['image_path'] = df_sample.apply(
        lambda row: f"images/image_train/image_{row['imageid']}_product_{row['productid']}.jpg",
        axis=1
    )
    
    # Connect to database
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    batch_name = f'week_{int((target_percentage - PIPELINE_CONFIG["initial_percentage"]) / PIPELINE_CONFIG["increment_percentage"]) + 1}'
    
    try:
        # Start batch tracking
        cursor.execute("""
            INSERT INTO data_loads (batch_name, percentage, total_rows, status, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            batch_name,
            target_percentage,
            target_rows,
            'running',
            {
                'type': 'incremental_load',
                'previous_percentage': current_pct,
                'increment': target_percentage - current_pct
            }
        ))
        batch_id = cursor.fetchone()[0]
        conn.commit()
        
        logger.info(f"Created batch record: {batch_name} (ID: {batch_id})")
        
        # Get existing product IDs to avoid duplicates
        cursor.execute("SELECT productid FROM products")
        existing_ids = set(row[0] for row in cursor.fetchall())
        
        # Filter out existing products
        df_new = df_sample[~df_sample['productid'].isin(existing_ids)]
        
        logger.info(f"New products to insert: {len(df_new)}")
        
        if len(df_new) > 0:
            # Insert products
            logger.info("Inserting new products...")
            products_data = [
                (
                    row['designation'],
                    row['description'],
                    row['productid'],
                    row['imageid'],
                    row['image_path']
                )
                for _, row in df_new.iterrows()
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
                for _, row in df_new.iterrows()
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
        
        logger.info("✅ Incremental data load completed successfully!")
        
        # Print summary
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT prdtypecode) FROM labels")
        classes_count = cursor.fetchone()[0]
        
        logger.info(f"\n📊 Database Summary:")
        logger.info(f"  - Products: {products_count}")
        logger.info(f"  - Classes: {classes_count}")
        logger.info(f"  - Percentage loaded: {target_percentage}%")
        logger.info(f"  - New products added: {len(df_new)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        conn.rollback()
        # Mark batch as failed
        try:
            cursor.execute("""
                UPDATE data_loads
                SET status = 'failed'
                WHERE batch_name = %s
            """, (batch_name,))
            conn.commit()
        except:
            pass
        return False
        
    finally:
        cursor.close()
        conn.close()


def get_load_history():
    """Get history of all data loads"""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                batch_name,
                percentage,
                total_rows,
                started_at,
                completed_at,
                status,
                metadata
            FROM data_loads
            ORDER BY started_at ASC
        """)
        
        results = cursor.fetchall()
        
        print("\n📜 Data Load History:")
        print("-" * 100)
        print(f"{'Batch':<20} {'%':<8} {'Rows':<10} {'Started':<20} {'Status':<12}")
        print("-" * 100)
        
        for row in results:
            batch_name, pct, rows, started, completed, status, metadata = row
            print(f"{batch_name:<20} {pct:<8.1f} {rows:<10} {started.strftime('%Y-%m-%d %H:%M'):<20} {status:<12}")
        
        print("-" * 100)
        
    finally:
        cursor.close()
        conn.close()


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Incremental Data Loader')
    parser.add_argument('--percentage', type=float, help='Target percentage to load')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--history', action='store_true', help='Show load history')
    
    args = parser.parse_args()
    
    if args.status:
        state = get_current_state()
        print("\n📊 Current State:")
        print(f"  - Percentage: {state['current_percentage']}%")
        print(f"  - Total rows: {state['total_rows']}")
        print(f"  - Last load: {state['last_load_date']}")
        print(f"  - Next increment: {calculate_next_percentage(state['current_percentage'])}%")
        return
    
    if args.history:
        get_load_history()
        return
    
    # Load data
    success = load_incremental_data(args.percentage)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

-- Rakuten MLOps Database Schema
-- Incremental Data Pipeline with Audit Trail
-- This file is executed in the context of rakuten_db database

-- Main products table (current state)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    designation TEXT,
    description TEXT,
    productid BIGINT UNIQUE NOT NULL,
    imageid BIGINT,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_productid ON products(productid);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at);

-- Labels/targets table
CREATE TABLE IF NOT EXISTS labels (
    id SERIAL PRIMARY KEY,
    productid BIGINT UNIQUE NOT NULL,
    prdtypecode INTEGER NOT NULL,
    FOREIGN KEY (productid) REFERENCES products(productid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_labels_productid ON labels(productid);
CREATE INDEX IF NOT EXISTS idx_labels_prdtypecode ON labels(prdtypecode);

-- Audit trail for products (tracks all changes)
CREATE TABLE IF NOT EXISTS products_history (
    history_id SERIAL PRIMARY KEY,
    product_id INTEGER,
    productid BIGINT NOT NULL,
    designation TEXT,
    description TEXT,
    imageid BIGINT,
    image_path TEXT,
    operation_type VARCHAR(10) NOT NULL,  -- 'INSERT' or 'UPDATE'
    operation_date TIMESTAMP DEFAULT NOW(),
    load_batch_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_products_history_date ON products_history(operation_date);
CREATE INDEX IF NOT EXISTS idx_products_history_batch ON products_history(load_batch_id);
CREATE INDEX IF NOT EXISTS idx_products_history_productid ON products_history(productid);

-- Track each data loading batch
CREATE TABLE IF NOT EXISTS data_loads (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(100) UNIQUE,
    percentage DECIMAL(5,2) NOT NULL,
    total_rows INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,  -- 'running', 'completed', 'failed'
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_data_loads_date ON data_loads(completed_at);
CREATE INDEX IF NOT EXISTS idx_data_loads_status ON data_loads(status);
CREATE INDEX IF NOT EXISTS idx_data_loads_percentage ON data_loads(percentage);

-- Trigger function to automatically populate products_history
CREATE OR REPLACE FUNCTION audit_products()
RETURNS TRIGGER AS $$
DECLARE
    current_batch_id INTEGER;
BEGIN
    -- Get the current running batch
    SELECT id INTO current_batch_id 
    FROM data_loads 
    WHERE status = 'running'
    ORDER BY started_at DESC 
    LIMIT 1;
    
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO products_history 
        (product_id, productid, designation, description, imageid, 
         image_path, operation_type, load_batch_id)
        VALUES 
        (NEW.id, NEW.productid, NEW.designation, NEW.description, 
         NEW.imageid, NEW.image_path, 'INSERT', current_batch_id);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO products_history 
        (product_id, productid, designation, description, imageid, 
         image_path, operation_type, load_batch_id)
        VALUES 
        (NEW.id, NEW.productid, NEW.designation, NEW.description, 
         NEW.imageid, NEW.image_path, 'UPDATE', current_batch_id);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for audit trail
DROP TRIGGER IF EXISTS products_audit_trigger ON products;
CREATE TRIGGER products_audit_trigger
AFTER INSERT OR UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION audit_products();

-- Create view for easy querying of current data state
CREATE OR REPLACE VIEW current_data_state AS
SELECT 
    dl.percentage,
    dl.total_rows,
    dl.completed_at,
    COUNT(p.id) as actual_rows,
    COUNT(DISTINCT l.prdtypecode) as num_classes
FROM data_loads dl
LEFT JOIN products p ON p.created_at <= dl.completed_at
LEFT JOIN labels l ON l.productid = p.productid
WHERE dl.status = 'completed'
GROUP BY dl.id, dl.percentage, dl.total_rows, dl.completed_at
ORDER BY dl.completed_at DESC;

-- Create view for class distribution
CREATE OR REPLACE VIEW class_distribution AS
SELECT 
    l.prdtypecode,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM labels l
JOIN products p ON p.productid = l.productid
GROUP BY l.prdtypecode
ORDER BY count DESC;

-- Grant permissions (adjust as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rakuten_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rakuten_user;

-- Insert initial state record (optional)
INSERT INTO data_loads (batch_name, percentage, total_rows, status, metadata)
VALUES ('initial', 0, 0, 'completed', '{"note": "Initial state before any data load"}')
ON CONFLICT (batch_name) DO NOTHING;


CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_customers (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL UNIQUE,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(5),
    customer_city VARCHAR(150),
    customer_state VARCHAR(2)
);

CREATE INDEX IF NOT EXISTS idx_dim_customers_unique_id
ON gold.dim_customers(customer_unique_id);

CREATE INDEX IF NOT EXISTS idx_dim_customers_state
ON gold.dim_customers(customer_state);

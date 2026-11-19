
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_sellers (
    seller_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id VARCHAR(32) NOT NULL UNIQUE,
    seller_zip_code_prefix VARCHAR(5),
    seller_city VARCHAR(150),
    seller_state VARCHAR(2)
);

CREATE INDEX IF NOT EXISTS idx_dim_sellers_state
ON gold.dim_sellers(seller_state);

CREATE INDEX IF NOT EXISTS idx_dim_sellers_city
ON gold.dim_sellers(seller_city);

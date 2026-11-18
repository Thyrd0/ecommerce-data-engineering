
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_products (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    product_id VARCHAR(32) NOT NULL UNIQUE,

    category_original VARCHAR(150),
    category_english VARCHAR(150) NOT NULL,

    product_name_length INTEGER,
    product_description_length INTEGER,
    product_photos_qty INTEGER,

    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER
);

CREATE INDEX IF NOT EXISTS idx_dim_products_category
ON gold.dim_products(category_english);


CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.fact_order_items (
    order_item_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    order_id VARCHAR(32) NOT NULL,
    order_item_id INTEGER NOT NULL,

    customer_key BIGINT NOT NULL
        REFERENCES gold.dim_customers(customer_key),

    product_key BIGINT NOT NULL
        REFERENCES gold.dim_products(product_key),

    seller_key BIGINT NOT NULL
        REFERENCES gold.dim_sellers(seller_key),

    date_key INTEGER NOT NULL
        REFERENCES gold.dim_dates(date_key),

    order_status VARCHAR(30) NOT NULL,

    quantity INTEGER NOT NULL DEFAULT 1,
    price NUMERIC(14,2) NOT NULL,
    freight_value NUMERIC(14,2) NOT NULL,

    total_value NUMERIC(14,2)
        GENERATED ALWAYS AS (price + freight_value) STORED,

    CONSTRAINT uq_fact_order_item
        UNIQUE (order_id, order_item_id),

    CONSTRAINT chk_fact_quantity
        CHECK (quantity = 1),

    CONSTRAINT chk_fact_price
        CHECK (price >= 0),

    CONSTRAINT chk_fact_freight
        CHECK (freight_value >= 0)
);

CREATE INDEX IF NOT EXISTS idx_fact_items_customer
ON gold.fact_order_items(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_items_product
ON gold.fact_order_items(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_items_seller
ON gold.fact_order_items(seller_key);

CREATE INDEX IF NOT EXISTS idx_fact_items_date
ON gold.fact_order_items(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_items_status
ON gold.fact_order_items(order_status);

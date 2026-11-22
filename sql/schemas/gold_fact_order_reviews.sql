
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.fact_order_reviews (
    review_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,

    customer_key BIGINT NOT NULL
        REFERENCES gold.dim_customers(customer_key),

    purchase_date_key INTEGER NOT NULL
        REFERENCES gold.dim_dates(date_key),

    review_creation_date_key INTEGER
        REFERENCES gold.dim_dates(date_key),

    review_answer_date_key INTEGER
        REFERENCES gold.dim_dates(date_key),

    review_score INTEGER NOT NULL,
    has_comment BOOLEAN NOT NULL,

    CONSTRAINT uq_fact_review
        UNIQUE (review_id, order_id),

    CONSTRAINT chk_review_score
        CHECK (review_score BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_reviews_customer
ON gold.fact_order_reviews(customer_key);

CREATE INDEX IF NOT EXISTS idx_reviews_purchase_date
ON gold.fact_order_reviews(purchase_date_key);

CREATE INDEX IF NOT EXISTS idx_reviews_creation_date
ON gold.fact_order_reviews(review_creation_date_key);

CREATE INDEX IF NOT EXISTS idx_reviews_score
ON gold.fact_order_reviews(review_score);

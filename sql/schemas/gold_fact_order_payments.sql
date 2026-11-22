
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.fact_order_payments (
    payment_key BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    order_id VARCHAR(32) NOT NULL,
    payment_sequential INTEGER NOT NULL,

    customer_key BIGINT NOT NULL
        REFERENCES gold.dim_customers(customer_key),

    date_key INTEGER NOT NULL
        REFERENCES gold.dim_dates(date_key),

    payment_type VARCHAR(30) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(14,2) NOT NULL,

    CONSTRAINT uq_fact_payment
        UNIQUE (order_id, payment_sequential),

    CONSTRAINT chk_payment_sequential
        CHECK (payment_sequential >= 1),

    CONSTRAINT chk_payment_installments
        CHECK (payment_installments >= 0),

    CONSTRAINT chk_payment_value
        CHECK (payment_value >= 0)
);

CREATE INDEX IF NOT EXISTS idx_fact_payments_customer
ON gold.fact_order_payments(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_payments_date
ON gold.fact_order_payments(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_payments_type
ON gold.fact_order_payments(payment_type);

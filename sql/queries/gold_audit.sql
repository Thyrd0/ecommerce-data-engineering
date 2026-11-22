-- Consulta 1. Integridad de registros Silver vs. Gold

SELECT
    'customers' AS tabla,
    (SELECT COUNT(*) FROM silver.customers) AS silver,
    (SELECT COUNT(*) FROM gold.dim_customers) AS gold

UNION ALL

SELECT
    'products',
    (SELECT COUNT(*) FROM silver.products),
    (SELECT COUNT(*) FROM gold.dim_products)

UNION ALL

SELECT
    'sellers',
    (SELECT COUNT(*) FROM silver.sellers),
    (SELECT COUNT(*) FROM gold.dim_sellers)

UNION ALL

SELECT
    'order_items',
    (SELECT COUNT(*) FROM silver.order_items),
    (SELECT COUNT(*) FROM gold.fact_order_items)

UNION ALL

SELECT
    'order_payments',
    (SELECT COUNT(*) FROM silver.order_payments),
    (SELECT COUNT(*) FROM gold.fact_order_payments)

UNION ALL

SELECT
    'order_reviews',
    (SELECT COUNT(*) FROM silver.order_reviews),
    (SELECT COUNT(*) FROM gold.fact_order_reviews);
    

-- Consulta 2. Integridad referencial

SELECT
    'items_customers' AS relacion,
    COUNT(*) AS referencias_invalidas
FROM gold.fact_order_items f
LEFT JOIN gold.dim_customers d
    ON f.customer_key = d.customer_key
WHERE d.customer_key IS NULL

UNION ALL

SELECT
    'items_products',
    COUNT(*)
FROM gold.fact_order_items f
LEFT JOIN gold.dim_products d
    ON f.product_key = d.product_key
WHERE d.product_key IS NULL

UNION ALL

SELECT
    'items_sellers',
    COUNT(*)
FROM gold.fact_order_items f
LEFT JOIN gold.dim_sellers d
    ON f.seller_key = d.seller_key
WHERE d.seller_key IS NULL

UNION ALL

SELECT
    'items_dates',
    COUNT(*)
FROM gold.fact_order_items f
LEFT JOIN gold.dim_dates d
    ON f.date_key = d.date_key
WHERE d.date_key IS NULL

UNION ALL

SELECT
    'payments_customers',
    COUNT(*)
FROM gold.fact_order_payments f
LEFT JOIN gold.dim_customers d
    ON f.customer_key = d.customer_key
WHERE d.customer_key IS NULL

UNION ALL

SELECT
    'payments_dates',
    COUNT(*)
FROM gold.fact_order_payments f
LEFT JOIN gold.dim_dates d
    ON f.date_key = d.date_key
WHERE d.date_key IS NULL

UNION ALL

SELECT
    'reviews_customers',
    COUNT(*)
FROM gold.fact_order_reviews f
LEFT JOIN gold.dim_customers d
    ON f.customer_key = d.customer_key
WHERE d.customer_key IS NULL

UNION ALL

SELECT
    'reviews_purchase_dates',
    COUNT(*)
FROM gold.fact_order_reviews f
LEFT JOIN gold.dim_dates d
    ON f.purchase_date_key = d.date_key
WHERE d.date_key IS NULL

UNION ALL

SELECT
    'reviews_creation_dates',
    COUNT(*)
FROM gold.fact_order_reviews f
LEFT JOIN gold.dim_dates d
    ON f.review_creation_date_key = d.date_key
WHERE f.review_creation_date_key IS NOT NULL
  AND d.date_key IS NULL

UNION ALL

SELECT
    'reviews_answer_dates',
    COUNT(*)
FROM gold.fact_order_reviews f
LEFT JOIN gold.dim_dates d
    ON f.review_answer_date_key = d.date_key
WHERE f.review_answer_date_key IS NOT NULL
  AND d.date_key IS NULL;


-- Consulta 3. Conciliación financiera

SELECT
    'importe_articulos' AS indicador,
    (SELECT SUM(price)
     FROM silver.order_items) AS silver,
    (SELECT SUM(price)
     FROM gold.fact_order_items) AS gold

UNION ALL

SELECT
    'importe_flete',
    (SELECT SUM(freight_value)
     FROM silver.order_items),
    (SELECT SUM(freight_value)
     FROM gold.fact_order_items)

UNION ALL

SELECT
    'importe_pagos',
    (SELECT SUM(payment_value)
     FROM silver.order_payments),
    (SELECT SUM(payment_value)
     FROM gold.fact_order_payments);


-- Consulta 4. Validar claves naturales y fechas

SELECT
    'customers' AS tabla,
    COUNT(*) AS registros,
    COUNT(DISTINCT customer_id) AS claves_unicas
FROM gold.dim_customers

UNION ALL

SELECT
    'products',
    COUNT(*),
    COUNT(DISTINCT product_id)
FROM gold.dim_products

UNION ALL

SELECT
    'sellers',
    COUNT(*),
    COUNT(DISTINCT seller_id)
FROM gold.dim_sellers

UNION ALL

SELECT
    'dates',
    COUNT(*),
    COUNT(DISTINCT date_key)
FROM gold.dim_dates;


-- Consulta 5. Confirmar ausencia de tablas de preparación

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'gold'
  AND table_name LIKE '\_%\_loading' ESCAPE '\'
ORDER BY table_name;


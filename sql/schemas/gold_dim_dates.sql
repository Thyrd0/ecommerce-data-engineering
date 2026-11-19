
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_dates (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,

    CONSTRAINT chk_month
        CHECK (month BETWEEN 1 AND 12),

    CONSTRAINT chk_quarter
        CHECK (quarter BETWEEN 1 AND 4),

    CONSTRAINT chk_day_of_week
        CHECK (day_of_week BETWEEN 1 AND 7)
);

CREATE INDEX IF NOT EXISTS idx_dim_dates_year_month
ON gold.dim_dates(year, month);

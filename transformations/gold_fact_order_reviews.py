
from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def get_engine():
    url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="localhost",
        port=5433,
        database=os.getenv("POSTGRES_DB"),
    )
    return create_engine(url)


def load_fact_reviews(engine):

    print("Preparando tabla de hechos de reseñas...")

    with engine.begin() as connection:

        expected = connection.execute(
            text("SELECT COUNT(*) FROM silver.order_reviews")
        ).scalar_one()

        # Validar todas las referencias antes de cargar.
        invalid = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM silver.order_reviews r
                LEFT JOIN silver.orders o
                    ON r.order_id = o.order_id
                LEFT JOIN gold.dim_customers c
                    ON o.customer_id = c.customer_id
                LEFT JOIN gold.dim_dates purchase_date
                    ON o.order_purchase_timestamp::date =
                       purchase_date.full_date
                LEFT JOIN gold.dim_dates creation_date
                    ON r.review_creation_date::date =
                       creation_date.full_date
                LEFT JOIN gold.dim_dates answer_date
                    ON r.review_answer_timestamp::date =
                       answer_date.full_date
                WHERE o.order_id IS NULL
                   OR c.customer_key IS NULL
                   OR purchase_date.date_key IS NULL
                   OR (
                       r.review_creation_date IS NOT NULL
                       AND creation_date.date_key IS NULL
                   )
                   OR (
                       r.review_answer_timestamp IS NOT NULL
                       AND answer_date.date_key IS NULL
                   )
            """)
        ).scalar_one()

        print(f"Reseñas esperadas: {expected:,}")
        print(f"Referencias inválidas: {invalid:,}")

        if invalid:
            raise ValueError(
                "Existen reseñas con referencias o fechas "
                "sin correspondencia en Gold. "
                "Revisa el calendario antes de continuar."
            )

        connection.execute(
            text("""
                DROP TABLE IF EXISTS
                    gold._fact_order_reviews_loading
            """)
        )

        connection.execute(
            text("""
                CREATE TABLE gold._fact_order_reviews_loading AS
                SELECT
                    r.review_id,
                    r.order_id,
                    c.customer_key,
                    purchase_date.date_key
                        AS purchase_date_key,
                    creation_date.date_key
                        AS review_creation_date_key,
                    answer_date.date_key
                        AS review_answer_date_key,
                    r.review_score,
                    (
                        NULLIF(
                            BTRIM(r.review_comment_message),
                            ''
                        ) IS NOT NULL
                    ) AS has_comment
                FROM silver.order_reviews r
                INNER JOIN silver.orders o
                    ON r.order_id = o.order_id
                INNER JOIN gold.dim_customers c
                    ON o.customer_id = c.customer_id
                INNER JOIN gold.dim_dates purchase_date
                    ON o.order_purchase_timestamp::date =
                       purchase_date.full_date
                LEFT JOIN gold.dim_dates creation_date
                    ON r.review_creation_date::date =
                       creation_date.full_date
                LEFT JOIN gold.dim_dates answer_date
                    ON r.review_answer_timestamp::date =
                       answer_date.full_date
            """)
        )

        staged = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold._fact_order_reviews_loading
            """)
        ).scalar_one()

        if staged != expected:
            raise ValueError(
                f"Staging contiene {staged} reseñas; "
                f"se esperaban {expected}."
            )

        connection.execute(
            text("""
                TRUNCATE TABLE gold.fact_order_reviews
                RESTART IDENTITY
            """)
        )

        connection.execute(
            text("""
                INSERT INTO gold.fact_order_reviews (
                    review_id,
                    order_id,
                    customer_key,
                    purchase_date_key,
                    review_creation_date_key,
                    review_answer_date_key,
                    review_score,
                    has_comment
                )
                SELECT
                    review_id,
                    order_id,
                    customer_key,
                    purchase_date_key,
                    review_creation_date_key,
                    review_answer_date_key,
                    review_score,
                    has_comment
                FROM gold._fact_order_reviews_loading
                ORDER BY order_id, review_id
            """)
        )

        total = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_order_reviews
            """)
        ).scalar_one()

        if total != expected:
            raise ValueError(
                "El total de reseñas no coincide con Silver."
            )

        connection.execute(
            text("""
                DROP TABLE gold._fact_order_reviews_loading
            """)
        )

    print(f"Reseñas cargadas en Gold: {total:,}")
    print("Staging eliminada correctamente.")
    print("gold.fact_order_reviews creada correctamente.")


def main():
    engine = get_engine()

    try:
        load_fact_reviews(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

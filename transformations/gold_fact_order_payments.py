
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


def load_fact_order_payments(engine):

    print("Preparando tabla de hechos de pagos...")

    with engine.begin() as connection:

        expected = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM silver.order_payments
            """)
        ).scalar_one()

        # Verificar correspondencia con dimensiones Gold
        invalid = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM silver.order_payments p
                LEFT JOIN silver.orders o
                    ON p.order_id = o.order_id
                LEFT JOIN gold.dim_customers c
                    ON o.customer_id = c.customer_id
                LEFT JOIN gold.dim_dates d
                    ON o.order_purchase_timestamp::date =
                       d.full_date
                WHERE o.order_id IS NULL
                   OR c.customer_key IS NULL
                   OR d.date_key IS NULL
            """)
        ).scalar_one()

        print(f"Pagos esperados: {expected:,}")
        print(f"Referencias inválidas: {invalid:,}")

        if invalid:
            raise ValueError(
                "Existen pagos sin correspondencia en Gold."
            )

        # Preparar registros
        connection.execute(
            text("""
                DROP TABLE IF EXISTS
                    gold._fact_order_payments_loading
            """)
        )

        connection.execute(
            text("""
                CREATE TABLE gold._fact_order_payments_loading AS
                SELECT
                    p.order_id,
                    p.payment_sequential,
                    c.customer_key,
                    d.date_key,
                    p.payment_type,
                    p.payment_installments,
                    p.payment_value
                FROM silver.order_payments p
                INNER JOIN silver.orders o
                    ON p.order_id = o.order_id
                INNER JOIN gold.dim_customers c
                    ON o.customer_id = c.customer_id
                INNER JOIN gold.dim_dates d
                    ON o.order_purchase_timestamp::date =
                       d.full_date
            """)
        )

        staged = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold._fact_order_payments_loading
            """)
        ).scalar_one()

        if staged != expected:
            raise ValueError(
                f"Staging contiene {staged} registros; "
                f"se esperaban {expected}."
            )

        # Publicar datos
        connection.execute(
            text("""
                TRUNCATE TABLE gold.fact_order_payments
                RESTART IDENTITY
            """)
        )

        connection.execute(
            text("""
                INSERT INTO gold.fact_order_payments (
                    order_id,
                    payment_sequential,
                    customer_key,
                    date_key,
                    payment_type,
                    payment_installments,
                    payment_value
                )
                SELECT
                    order_id,
                    payment_sequential,
                    customer_key,
                    date_key,
                    payment_type,
                    payment_installments,
                    payment_value
                FROM gold._fact_order_payments_loading
                ORDER BY order_id, payment_sequential
            """)
        )

        total = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_order_payments
            """)
        ).scalar_one()

        if total != expected:
            raise ValueError(
                "El total cargado no coincide con Silver."
            )

        # Validar importe total contra Silver
        amounts = connection.execute(
            text("""
                SELECT
                    (SELECT SUM(payment_value)
                     FROM silver.order_payments),
                    (SELECT SUM(payment_value)
                     FROM gold.fact_order_payments)
            """)
        ).one()

        if amounts[0] != amounts[1]:
            raise ValueError(
                "Los importes de Silver y Gold no coinciden."
            )

        # Limpiar staging
        connection.execute(
            text("""
                DROP TABLE gold._fact_order_payments_loading
            """)
        )

    print(f"Pagos cargados en Gold: {total:,}")
    print("Importes de Silver y Gold coinciden.")
    print("Tabla de preparación eliminada.")
    print("gold.fact_order_payments creada correctamente.")


def main():
    engine = get_engine()

    try:
        load_fact_order_payments(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

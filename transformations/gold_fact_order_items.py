
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


def load_fact_order_items(engine):

    print("Preparando tabla de hechos...")

    # Validar que no existan referencias faltantes.
    validation_sql = """
        SELECT COUNT(*)
        FROM silver.order_items oi
        JOIN silver.orders o
            ON oi.order_id = o.order_id
        LEFT JOIN gold.dim_customers c
            ON o.customer_id = c.customer_id
        LEFT JOIN gold.dim_products p
            ON oi.product_id = p.product_id
        LEFT JOIN gold.dim_sellers s
            ON oi.seller_id = s.seller_id
        LEFT JOIN gold.dim_dates d
            ON o.order_purchase_timestamp::date = d.full_date
        WHERE c.customer_key IS NULL
           OR p.product_key IS NULL
           OR s.seller_key IS NULL
           OR d.date_key IS NULL
    """

    with engine.begin() as connection:

        expected = connection.execute(
            text("SELECT COUNT(*) FROM silver.order_items")
        ).scalar_one()

        invalid = connection.execute(
            text(validation_sql)
        ).scalar_one()

        print(f"Artículos esperados: {expected:,}")
        print(f"Referencias inválidas: {invalid:,}")

        if invalid > 0:
            raise ValueError(
                "Existen artículos sin correspondencia "
                "en las dimensiones Gold."
            )

        # Tabla de preparación.
        connection.execute(
            text("""
                DROP TABLE IF EXISTS gold._fact_order_items_loading
            """)
        )

        connection.execute(
            text("""
                CREATE TABLE gold._fact_order_items_loading AS
                SELECT
                    oi.order_id,
                    oi.order_item_id,
                    c.customer_key,
                    p.product_key,
                    s.seller_key,
                    d.date_key,
                    o.order_status,
                    1::INTEGER AS quantity,
                    oi.price,
                    oi.freight_value
                FROM silver.order_items oi
                INNER JOIN silver.orders o
                    ON oi.order_id = o.order_id
                INNER JOIN gold.dim_customers c
                    ON o.customer_id = c.customer_id
                INNER JOIN gold.dim_products p
                    ON oi.product_id = p.product_id
                INNER JOIN gold.dim_sellers s
                    ON oi.seller_id = s.seller_id
                INNER JOIN gold.dim_dates d
                    ON o.order_purchase_timestamp::date = d.full_date
            """)
        )

        staged = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold._fact_order_items_loading
            """)
        ).scalar_one()

        if staged != expected:
            raise ValueError(
                f"Staging contiene {staged} registros, "
                f"pero se esperaban {expected}."
            )

        # Carga completa de la tabla de hechos.
        connection.execute(
            text("""
                TRUNCATE TABLE gold.fact_order_items
                RESTART IDENTITY
            """)
        )

        connection.execute(
            text("""
                INSERT INTO gold.fact_order_items (
                    order_id,
                    order_item_id,
                    customer_key,
                    product_key,
                    seller_key,
                    date_key,
                    order_status,
                    quantity,
                    price,
                    freight_value
                )
                SELECT
                    order_id,
                    order_item_id,
                    customer_key,
                    product_key,
                    seller_key,
                    date_key,
                    order_status,
                    quantity,
                    price,
                    freight_value
                FROM gold._fact_order_items_loading
                ORDER BY order_id, order_item_id
            """)
        )

        total = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_order_items
            """)
        ).scalar_one()

        if total != expected:
            raise ValueError(
                "La cantidad cargada no coincide con Silver."
            )

        # Eliminar staging.
        connection.execute(
            text("""
                DROP TABLE gold._fact_order_items_loading
            """)
        )

    print(f"Artículos cargados en Gold: {total:,}")
    print("Tabla gold.fact_order_items creada correctamente.")


def main():
    engine = get_engine()

    try:
        load_fact_order_items(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

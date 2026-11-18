
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


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


def load_dim_customers(engine):

    print("Leyendo silver.customers...")

    df = pd.read_sql(
        """
        SELECT
            customer_id,
            customer_unique_id,
            customer_zip_code_prefix,
            customer_city,
            customer_state
        FROM silver.customers
        """,
        engine
    )

    print(f"Clientes encontrados: {len(df):,}")

    if df["customer_id"].isna().any():
        raise ValueError("Existen customer_id nulos.")

    if df["customer_id"].duplicated().any():
        raise ValueError("Existen customer_id duplicados.")

    if df["customer_unique_id"].isna().any():
        raise ValueError("Existen customer_unique_id nulos.")

    # Cargar a una tabla temporal de preparación.
    # La tabla definitiva conserva sus restricciones.
    df.to_sql(
        "_dim_customers_loading",
        engine,
        schema="gold",
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi"
    )

    # Carga completa e idempotente.
    # Si se vuelve a ejecutar, no duplica clientes.
    with engine.begin() as connection:

        connection.execute(
            text("TRUNCATE TABLE gold.dim_customers RESTART IDENTITY")
        )

        connection.execute(
            text("""
                INSERT INTO gold.dim_customers (
                    customer_id,
                    customer_unique_id,
                    customer_zip_code_prefix,
                    customer_city,
                    customer_state
                )
                SELECT
                    customer_id,
                    customer_unique_id,
                    customer_zip_code_prefix,
                    customer_city,
                    customer_state
                FROM gold._dim_customers_loading
                ORDER BY customer_id
            """)
        )

        total = connection.execute(
            text("SELECT COUNT(*) FROM gold.dim_customers")
        ).scalar_one()

        if total != len(df):
            raise ValueError(
                "El número de clientes cargados no coincide."
            )

    print(f"Clientes cargados en Gold: {total:,}")
    print("gold.dim_customers creada correctamente.")


def main():
    engine = get_engine()

    try:
        load_dim_customers(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()


from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text
from sqlalchemy.types import DateTime, String


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


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


def transform_orders(engine):
    print("Leyendo bronze.orders...")

    df = pd.read_sql(
        "SELECT * FROM bronze.orders",
        engine
    )

    original_rows = len(df)

    # Estandarizar nombres de columnas
    df.columns = df.columns.str.lower().str.strip()

    # Limpiar campos de texto
    for column in ["order_id", "customer_id", "order_status"]:
        df[column] = df[column].astype("string").str.strip()

    df["order_status"] = df["order_status"].str.lower()

    # Convertir fechas
    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

    # Validar identificadores obligatorios
    if df["order_id"].isna().any():
        raise ValueError("Existen pedidos sin order_id.")

    if (df["order_id"] == "").any():
        raise ValueError("Existen order_id vacíos.")

    if df["order_id"].duplicated().any():
        raise ValueError("Existen order_id duplicados.")

    # Conservar fechas faltantes:
    # pueden corresponder a pedidos no entregados
    print(f"Filas originales: {original_rows:,}")
    print(f"Filas transformadas: {len(df):,}")

    print("\nValores nulos por columna:")
    print(df.isna().sum())

    # Escribir en una tabla temporal
    staging_table = "_orders_loading"

    df.to_sql(
        staging_table,
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "order_id": String(32),
            "customer_id": String(32),
            "order_status": String(30),
            **{
                column: DateTime()
                for column in DATE_COLUMNS
            },
        }
    )

    # Publicar la tabla cargada
    with engine.begin() as connection:
        connection.execute(
            text("DROP TABLE IF EXISTS silver.orders")
        )
        connection.execute(
            text(
                "ALTER TABLE silver._orders_loading "
                "RENAME TO orders"
            )
        )

    print("\nTabla silver.orders creada correctamente.")


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_orders(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

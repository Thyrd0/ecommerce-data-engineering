
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text
from sqlalchemy.types import (
    String, Integer, Numeric, DateTime
)


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


def transform_order_items(engine):

    print("Leyendo bronze.order_items...")

    df = pd.read_sql(
        "SELECT * FROM bronze.order_items",
        engine
    )

    original_rows = len(df)

    df.columns = df.columns.str.lower().str.strip()

    # Limpiar identificadores
    for column in ["order_id", "product_id", "seller_id"]:
        df[column] = df[column].astype("string").str.strip()

        if df[column].isna().any() or df[column].eq("").any():
            raise ValueError(
                f"Hay identificadores faltantes en {column}"
            )

    # Convertir ID del artículo
    df["order_item_id"] = pd.to_numeric(
        df["order_item_id"], errors="raise"
    ).astype("int64")

    # Convertir importes a números
    for column in ["price", "freight_value"]:
        df[column] = pd.to_numeric(
            df[column], errors="raise"
        )

        if df[column].isna().any():
            raise ValueError(f"Hay importes nulos en {column}")

        if (df[column] < 0).any():
            raise ValueError(
                f"Hay valores negativos en {column}"
            )

        # Validar máximo dos decimales
        if ((df[column] * 100).round(6) % 1 != 0).any():
            raise ValueError(
                f"Hay importes con más de dos decimales: {column}"
            )

        # Convertir a decimal exacto para PostgreSQL
        df[column] = df[column].map(
            lambda value: f"{value:.2f}"
        )

    # Convertir fecha
    df["shipping_limit_date"] = pd.to_datetime(
        df["shipping_limit_date"],
        errors="raise"
    )

    # Verificar clave compuesta
    duplicate_keys = df.duplicated(
        subset=["order_id", "order_item_id"]
    ).sum()

    if duplicate_keys > 0:
        raise ValueError(
            f"Se encontraron {duplicate_keys} claves duplicadas"
        )

    print(f"Filas originales: {original_rows:,}")
    print(f"Filas transformadas: {len(df):,}")
    print(f"Claves duplicadas: {duplicate_keys}")

    # Crear tabla de preparación
    df.to_sql(
        "_order_items_loading",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "order_id": String(32),
            "order_item_id": Integer(),
            "product_id": String(32),
            "seller_id": String(32),
            "shipping_limit_date": DateTime(),
            "price": Numeric(12, 2),
            "freight_value": Numeric(12, 2),
        }
    )

    # Publicar de forma transaccional
    with engine.begin() as connection:
        connection.execute(
            text("DROP TABLE IF EXISTS silver.order_items")
        )
        connection.execute(
            text(
                "ALTER TABLE silver._order_items_loading "
                "RENAME TO order_items"
            )
        )

    print("\nTabla silver.order_items creada correctamente.")


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_order_items(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

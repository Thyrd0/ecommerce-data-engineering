
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text


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


def transform_customers(engine):
    print("Leyendo bronze.customers...")

    df = pd.read_sql(
        "SELECT * FROM bronze.customers",
        engine
    )

    original_rows = len(df)

    # Estandarizar nombres de columnas
    df.columns = df.columns.str.lower().str.strip()

    # Limpiar espacios y estandarizar valores de texto
    text_columns = [
        "customer_id",
        "customer_unique_id",
        "customer_city",
        "customer_state",
    ]

    for column in text_columns:
        df[column] = df[column].astype("string").str.strip()

    df["customer_city"] = df["customer_city"].str.lower()
    df["customer_state"] = df["customer_state"].str.upper()

    # Convertir código postal a entero anulable
    df["customer_zip_code_prefix"] = (
        df["customer_zip_code_prefix"]
        .astype("string")
        .str.strip()
        .str.zfill(5)
    )

    # Eliminar duplicados exactos
    df = df.drop_duplicates()

    # Validar identificadores obligatorios
    df = df.dropna(subset=["customer_id", "customer_unique_id"])
    df = df[
        (df["customer_id"] != "") &
        (df["customer_unique_id"] != "")
    ]

    if df["customer_id"].duplicated().any():
        raise ValueError(
            "Existen customer_id duplicados en Silver."
        )

    print(f"Filas originales: {original_rows:,}")
    print(f"Filas transformadas: {len(df):,}")

    # Guardar tabla Silver
    df.to_sql(
        "customers",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000
    )

    print("Tabla silver.customers creada correctamente.")


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_customers(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

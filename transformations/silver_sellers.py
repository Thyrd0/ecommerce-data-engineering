
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.types import String


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


def transform_sellers(engine):

    print("Leyendo bronze.sellers...")

    df = pd.read_sql(
        "SELECT * FROM bronze.sellers",
        engine
    )

    original_rows = len(df)
    df.columns = df.columns.str.lower().str.strip()

    # Estandarizar identificadores
    df["seller_id"] = (
        df["seller_id"]
        .astype("string")
        .str.strip()
    )

    # Conservar códigos postales como texto
    df["seller_zip_code_prefix"] = (
        df["seller_zip_code_prefix"]
        .astype("string")
        .str.strip()
        .str.zfill(5)
    )

    # Normalizar ciudad y estado
    df["seller_city"] = (
        df["seller_city"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    df["seller_state"] = (
        df["seller_state"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # Validar campos obligatorios
    for column in df.columns:
        if (
            df[column].isna().any()
            or df[column].eq("").any()
        ):
            raise ValueError(
                f"Existen valores faltantes en {column}"
            )

    # Validar códigos postales
    valid_zip = df["seller_zip_code_prefix"].str.fullmatch(
        r"\d{5}"
    )

    if not valid_zip.all():
        raise ValueError(
            "Existen códigos postales con formato inválido."
        )

    # Validar identificadores únicos
    duplicate_ids = df["seller_id"].duplicated().sum()

    if duplicate_ids:
        raise ValueError(
            f"Se encontraron {duplicate_ids} seller_id duplicados."
        )

    print(f"Filas originales: {original_rows:,}")
    print(f"Filas transformadas: {len(df):,}")
    print(f"Identificadores duplicados: {duplicate_ids}")

    # Preparar tabla temporal
    df.to_sql(
        "_sellers_loading",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "seller_id": String(32),
            "seller_zip_code_prefix": String(5),
            "seller_city": String(100),
            "seller_state": String(2),
        }
    )

    # Publicar tabla
    with engine.begin() as connection:
        connection.execute(
            text("DROP TABLE IF EXISTS silver.sellers")
        )
        connection.execute(
            text(
                "ALTER TABLE silver._sellers_loading "
                "RENAME TO sellers"
            )
        )

    print(
        "\nTabla silver.sellers creada correctamente."
    )


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_sellers(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

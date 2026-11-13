
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text
from sqlalchemy.types import String, Integer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


NUMERIC_COLUMNS = [
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
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


def transform_products(engine):

    print("Leyendo bronze.products...")

    df = pd.read_sql(
        "SELECT * FROM bronze.products",
        engine
    )

    original_rows = len(df)

    df.columns = df.columns.str.lower().str.strip()

    # Corregir errores ortográficos del dataset original
    df = df.rename(columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length",
    })

    # Estandarizar identificadores y categorías
    df["product_id"] = (
        df["product_id"]
        .astype("string")
        .str.strip()
    )

    df["product_category_name"] = (
        df["product_category_name"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # Validar identificadores
    if df["product_id"].isna().any():
        raise ValueError("Existen productos sin product_id.")

    if df["product_id"].eq("").any():
        raise ValueError("Existen product_id vacíos.")

    if df["product_id"].duplicated().any():
        raise ValueError("Existen product_id duplicados.")

    # Convertir atributos numéricos
    renamed_numeric_columns = [
        "product_name_length",
        "product_description_length",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]

    for column in renamed_numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).astype("Int64")

        # Valores negativos no son válidos
        if (df[column].dropna() < 0).any():
            raise ValueError(
                f"Se encontraron valores negativos en {column}"
            )

    # Reporte de calidad
    print(f"Filas originales: {original_rows:,}")
    print(f"Filas transformadas: {len(df):,}")

    print("\nValores nulos por columna:")
    print(df.isna().sum())

    print("\nProductos sin categoría:")
    print(df["product_category_name"].isna().sum())

    # Preparar tabla temporal
    df.to_sql(
        "_products_loading",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "product_id": String(32),
            "product_category_name": String(100),
            **{
                column: Integer()
                for column in renamed_numeric_columns
            },
        }
    )

    # Publicar tabla Silver
    with engine.begin() as connection:
        connection.execute(
            text("DROP TABLE IF EXISTS silver.products")
        )
        connection.execute(
            text(
                "ALTER TABLE silver._products_loading "
                "RENAME TO products"
            )
        )

    print("\nTabla silver.products creada correctamente.")


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_products(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

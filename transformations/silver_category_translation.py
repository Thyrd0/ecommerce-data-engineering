
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


def transform_categories(engine):

    print("Leyendo bronze.category_translation...")

    df = pd.read_sql(
        "SELECT * FROM bronze.category_translation",
        engine
    )

    original_rows = len(df)

    df.columns = df.columns.str.lower().str.strip()

    expected_columns = [
        "product_category_name",
        "product_category_name_english"
    ]

    if set(df.columns) != set(expected_columns):
        raise ValueError(
            f"Columnas inesperadas: {df.columns.tolist()}"
        )

    # Estandarizar categorías
    for column in expected_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    # Validar valores obligatorios
    for column in expected_columns:
        if (
            df[column].isna().any()
            or df[column].eq("").any()
        ):
            raise ValueError(
                f"Existen valores faltantes en {column}"
            )

    # Eliminar duplicados exactos
    df = df.drop_duplicates()

    # Validar unicidad de categoría original
    duplicate_categories = df[
        "product_category_name"
    ].duplicated().sum()

    if duplicate_categories:
        raise ValueError(
            f"Existen {duplicate_categories} categorías repetidas."
        )

    print(f"Filas originales: {original_rows:,}")
    print(f"Filas transformadas: {len(df):,}")
    print(f"Categorías duplicadas: {duplicate_categories}")

    # Crear tabla de preparación
    df.to_sql(
        "_category_translation_loading",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=1000,
        dtype={
            "product_category_name": String(100),
            "product_category_name_english": String(100),
        }
    )

    # Publicar tabla
    with engine.begin() as connection:
        connection.execute(
            text(
                "DROP TABLE IF EXISTS silver.category_translation"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE silver._category_translation_loading "
                "RENAME TO category_translation"
            )
        )

    print(
        "\nTabla silver.category_translation creada correctamente."
    )


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_categories(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

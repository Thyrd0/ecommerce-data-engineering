
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.types import String, Integer


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


def load_dim_products(engine):

    print("Leyendo productos y categorías desde Silver...")

    query = """
        SELECT
            p.product_id,
            p.product_category_name AS category_original,
            c.product_category_name_english AS category_english,
            p.product_name_length,
            p.product_description_length,
            p.product_photos_qty,
            p.product_weight_g,
            p.product_length_cm,
            p.product_height_cm,
            p.product_width_cm
        FROM silver.products p
        LEFT JOIN silver.category_translation c
            ON p.product_category_name = c.product_category_name
    """

    df = pd.read_sql(query, engine)

    print(f"Productos leídos: {len(df):,}")

    # Validar identificadores
    if df["product_id"].isna().any():
        raise ValueError("Existen product_id nulos.")

    if df["product_id"].duplicated().any():
        raise ValueError(
            "Existen product_id duplicados después del JOIN."
        )

    # Clasificar categorías faltantes
    missing_original = df["category_original"].isna()

    missing_translation = (
        df["category_original"].notna()
        & df["category_english"].isna()
    )

    print(
        f"Productos sin categoría original: "
        f"{missing_original.sum():,}"
    )

    print(
        f"Productos sin traducción: "
        f"{missing_translation.sum():,}"
    )

    df.loc[
        missing_original, "category_english"
    ] = "unknown"

    df.loc[
        missing_translation, "category_english"
    ] = "untranslated"

    # Comprobar que no queden categorías inglesas nulas
    if df["category_english"].isna().any():
        raise ValueError(
            "Quedaron categorías sin clasificar."
        )

    # Validar que la unión no alteró el número de productos
    with engine.connect() as connection:
        expected_rows = connection.execute(
            text("SELECT COUNT(*) FROM silver.products")
        ).scalar_one()

    if len(df) != expected_rows:
        raise ValueError(
            "La cantidad de productos no coincide con Silver."
        )

    # Tabla de preparación
    print("\nCargando tabla de preparación...")

    df.to_sql(
        "_dim_products_loading",
        engine,
        schema="gold",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "product_id": String(32),
            "category_original": String(150),
            "category_english": String(150),
            "product_name_length": Integer(),
            "product_description_length": Integer(),
            "product_photos_qty": Integer(),
            "product_weight_g": Integer(),
            "product_length_cm": Integer(),
            "product_height_cm": Integer(),
            "product_width_cm": Integer(),
        }
    )

    # Publicar en Gold y limpiar staging
    with engine.begin() as connection:

        connection.execute(
            text(
                "TRUNCATE TABLE gold.dim_products "
                "RESTART IDENTITY"
            )
        )

        connection.execute(
            text("""
                INSERT INTO gold.dim_products (
                    product_id,
                    category_original,
                    category_english,
                    product_name_length,
                    product_description_length,
                    product_photos_qty,
                    product_weight_g,
                    product_length_cm,
                    product_height_cm,
                    product_width_cm
                )
                SELECT
                    product_id,
                    category_original,
                    category_english,
                    product_name_length,
                    product_description_length,
                    product_photos_qty,
                    product_weight_g,
                    product_length_cm,
                    product_height_cm,
                    product_width_cm
                FROM gold._dim_products_loading
                ORDER BY product_id
            """)
        )

        total = connection.execute(
            text(
                "SELECT COUNT(*) FROM gold.dim_products"
            )
        ).scalar_one()

        if total != expected_rows:
            raise ValueError(
                "El total cargado no coincide con Silver."
            )

        # Eliminar tabla de preparación
        connection.execute(
            text(
                "DROP TABLE IF EXISTS "
                "gold._dim_products_loading"
            )
        )

    print(f"\nProductos cargados en Gold: {total:,}")
    print("Tabla gold.dim_products creada correctamente.")


def main():
    engine = get_engine()

    try:
        load_dim_products(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

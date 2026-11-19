
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


def load_dim_sellers(engine):

    print("Leyendo silver.sellers...")

    query = """
        SELECT
            seller_id,
            seller_zip_code_prefix,
            seller_city,
            seller_state
        FROM silver.sellers
    """

    df = pd.read_sql(query, engine)

    original_rows = len(df)

    print(f"Vendedores encontrados: {original_rows:,}")

    # Validar identificadores
    if df["seller_id"].isna().any():
        raise ValueError("Existen seller_id nulos.")

    if df["seller_id"].duplicated().any():
        raise ValueError("Existen seller_id duplicados.")

    # Validar códigos postales
    invalid_zip = ~df[
        "seller_zip_code_prefix"
    ].astype("string").str.fullmatch(r"\d{5}").fillna(False)

    if invalid_zip.any():
        raise ValueError(
            f"Existen {invalid_zip.sum()} códigos postales inválidos."
        )

    # Cargar datos a staging
    print("\nCargando tabla de preparación...")

    df.to_sql(
        "_dim_sellers_loading",
        engine,
        schema="gold",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "seller_id": String(32),
            "seller_zip_code_prefix": String(5),
            "seller_city": String(150),
            "seller_state": String(2),
        }
    )

    # Publicar datos en Gold
    with engine.begin() as connection:

        connection.execute(
            text("""
                TRUNCATE TABLE gold.dim_sellers
                RESTART IDENTITY
            """)
        )

        connection.execute(
            text("""
                INSERT INTO gold.dim_sellers (
                    seller_id,
                    seller_zip_code_prefix,
                    seller_city,
                    seller_state
                )
                SELECT
                    seller_id,
                    seller_zip_code_prefix,
                    seller_city,
                    seller_state
                FROM gold._dim_sellers_loading
                ORDER BY seller_id
            """)
        )

        total = connection.execute(
            text("SELECT COUNT(*) FROM gold.dim_sellers")
        ).scalar_one()

        if total != original_rows:
            raise ValueError(
                "La cantidad de vendedores cargados no coincide."
            )

        # Eliminar staging después de una carga correcta
        connection.execute(
            text("""
                DROP TABLE IF EXISTS gold._dim_sellers_loading
            """)
        )

    print(f"\nVendedores cargados en Gold: {total:,}")
    print("Tabla gold.dim_sellers creada correctamente.")


def main():
    engine = get_engine()

    try:
        load_dim_sellers(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

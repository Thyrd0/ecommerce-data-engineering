
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.types import String, Float


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


def transform_geolocation(engine):

    print("Leyendo bronze.geolocation...")

    df = pd.read_sql(
        "SELECT * FROM bronze.geolocation",
        engine
    )

    original_rows = len(df)
    df.columns = df.columns.str.lower().str.strip()

    # Conservar código postal como texto
    df["geolocation_zip_code_prefix"] = (
        df["geolocation_zip_code_prefix"]
        .astype("string")
        .str.strip()
        .str.zfill(5)
    )

    # Normalizar ciudad y estado
    df["geolocation_city"] = (
        df["geolocation_city"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    df["geolocation_state"] = (
        df["geolocation_state"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # Convertir coordenadas
    for column in [
        "geolocation_lat",
        "geolocation_lng"
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Validar campos obligatorios
    if df.isna().any().any():
        raise ValueError(
            "Existen valores nulos después de transformar."
        )

    # Validar rangos geográficos generales
    invalid_coordinates = (
        ~df["geolocation_lat"].between(-90, 90)
        | ~df["geolocation_lng"].between(-180, 180)
    )

    if invalid_coordinates.any():
        raise ValueError(
            f"Existen {invalid_coordinates.sum()} "
            "coordenadas fuera de rango."
        )

    # Deduplicación exacta después de normalizar
    df = df.drop_duplicates()

    removed_rows = original_rows - len(df)

    print(f"Filas originales: {original_rows:,}")
    print(f"Duplicados eliminados: {removed_rows:,}")
    print(f"Filas transformadas: {len(df):,}")

    # Preparar tabla temporal
    df.to_sql(
        "_geolocation_loading",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "geolocation_zip_code_prefix": String(5),
            "geolocation_lat": Float(),
            "geolocation_lng": Float(),
            "geolocation_city": String(150),
            "geolocation_state": String(2),
        }
    )

    # Publicar tabla
    with engine.begin() as connection:
        connection.execute(
            text(
                "DROP TABLE IF EXISTS silver.geolocation"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE silver._geolocation_loading "
                "RENAME TO geolocation"
            )
        )

    print(
        "\nTabla silver.geolocation creada correctamente."
    )


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_geolocation(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

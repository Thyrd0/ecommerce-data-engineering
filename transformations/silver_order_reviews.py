
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.types import String, Integer, DateTime, Text


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


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


def transform_reviews(engine):

    print("Leyendo bronze.order_reviews...")

    df = pd.read_sql(
        "SELECT * FROM bronze.order_reviews",
        engine
    )

    original_rows = len(df)

    df.columns = df.columns.str.lower().str.strip()

    # Limpiar identificadores
    for column in ["review_id", "order_id"]:
        df[column] = df[column].astype("string").str.strip()

        if df[column].isna().any() or df[column].eq("").any():
            raise ValueError(
                f"Identificadores faltantes en {column}"
            )

    # Convertir calificación a entero
    df["review_score"] = pd.to_numeric(
        df["review_score"],
        errors="raise"
    ).astype("Int64")

    if df["review_score"].isna().any():
        raise ValueError("Existen calificaciones nulas.")

    if not df["review_score"].between(1, 5).all():
        raise ValueError(
            "Existen calificaciones fuera del rango 1-5."
        )

    # Limpiar comentarios opcionales
    for column in [
        "review_comment_title",
        "review_comment_message"
    ]:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # Convertir fechas
    for column in [
        "review_creation_date",
        "review_answer_timestamp"
    ]:
        df[column] = pd.to_datetime(
            df[column],
            errors="raise"
        )

    # No asumir que review_id es único:
    # validar la combinación review_id + order_id
    duplicate_keys = df.duplicated(
        subset=["review_id", "order_id"]
    ).sum()

    print(f"Filas originales: {original_rows:,}")
    print(f"Claves compuestas repetidas: {duplicate_keys:,}")

    if duplicate_keys:
        print(
            "AVISO: Se conservarán las filas originales "
            "para analizar posibles duplicados."
        )

    print("\nValores nulos por columna:")
    print(df.isna().sum())

    # Publicar tabla Silver
    df.to_sql(
        "_order_reviews_loading",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "review_id": String(32),
            "order_id": String(32),
            "review_score": Integer(),
            "review_comment_title": Text(),
            "review_comment_message": Text(),
            "review_creation_date": DateTime(),
            "review_answer_timestamp": DateTime(),
        }
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                "DROP TABLE IF EXISTS silver.order_reviews"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE silver._order_reviews_loading "
                "RENAME TO order_reviews"
            )
        )

    print(
        f"\nFilas transformadas: {len(df):,}"
    )
    print(
        "Tabla silver.order_reviews creada correctamente."
    )


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_reviews(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

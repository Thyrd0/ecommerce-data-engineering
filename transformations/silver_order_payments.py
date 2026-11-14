
from pathlib import Path
import os
from decimal import Decimal, InvalidOperation

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text
from sqlalchemy.types import String, Integer, Numeric


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


def parse_amount(value):
    if pd.isna(value):
        raise ValueError("Importe de pago faltante")

    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(
            f"Importe de pago inválido: {value}"
        ) from error

    if not amount.is_finite() or amount < 0:
        raise ValueError(
            f"Importe de pago no válido: {value}"
        )

    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError(
            f"Importe con más de dos decimales: {value}"
        )

    return amount


def transform_payments(engine):
    print("Leyendo bronze.order_payments...")

    df = pd.read_sql(
        "SELECT * FROM bronze.order_payments",
        engine
    )

    original_rows = len(df)
    df.columns = df.columns.str.lower().str.strip()

    # Limpiar identificadores
    df["order_id"] = (
        df["order_id"].astype("string").str.strip()
    )

    if (
        df["order_id"].isna().any()
        or df["order_id"].eq("").any()
    ):
        raise ValueError("Existen order_id faltantes.")

    # Normalizar métodos de pago
    df["payment_type"] = (
        df["payment_type"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    if (
        df["payment_type"].isna().any()
        or df["payment_type"].eq("").any()
    ):
        raise ValueError("Existen tipos de pago faltantes.")

    # Convertir secuencia y cuotas
    for column in [
        "payment_sequential",
        "payment_installments"
    ]:
        values = pd.to_numeric(
            df[column],
            errors="raise"
        )

        if (
            values.isna().any()
            or (values % 1 != 0).any()
            or (values < 0).any()
        ):
            raise ValueError(
                f"Valores inválidos en {column}"
            )

        df[column] = values.astype("int64")

    if (df["payment_sequential"] < 1).any():
        raise ValueError(
            "payment_sequential debe ser positivo."
        )

    # Importes monetarios exactos
    df["payment_value"] = df["payment_value"].map(
        parse_amount
    )

    # Verificar clave compuesta
    duplicate_keys = df.duplicated(
        subset=["order_id", "payment_sequential"]
    ).sum()

    if duplicate_keys:
        raise ValueError(
            f"Se encontraron {duplicate_keys} claves duplicadas."
        )

    print(f"Filas originales: {original_rows:,}")
    print(f"Filas transformadas: {len(df):,}")
    print(f"Claves duplicadas: {duplicate_keys}")

    # Preparar tabla
    df.to_sql(
        "_order_payments_loading",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "order_id": String(32),
            "payment_sequential": Integer(),
            "payment_type": String(30),
            "payment_installments": Integer(),
            "payment_value": Numeric(14, 2),
        }
    )

    # Publicar tabla
    with engine.begin() as connection:
        connection.execute(
            text(
                "DROP TABLE IF EXISTS silver.order_payments"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE silver._order_payments_loading "
                "RENAME TO order_payments"
            )
        )

    print(
        "\nTabla silver.order_payments creada correctamente."
    )


def main():
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS silver")
            )

        transform_payments(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

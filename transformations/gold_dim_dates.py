
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.types import Integer, Date, String, Boolean


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


MONTH_NAMES = [
    "enero", "febrero", "marzo", "abril",
    "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre"
]

DAY_NAMES = [
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo"
]


def load_dim_dates(engine):

    print("Identificando rango de fechas en Silver...")

    # Considerar todas las fechas relevantes para
    # los futuros análisis de pedidos y entregas.
    query = """
        SELECT
            MIN(event_date) AS min_date,
            MAX(event_date) AS max_date
        FROM (
            SELECT order_purchase_timestamp::date AS event_date
            FROM silver.orders

            UNION ALL

            SELECT order_approved_at::date
            FROM silver.orders

            UNION ALL

            SELECT order_delivered_carrier_date::date
            FROM silver.orders

            UNION ALL

            SELECT order_delivered_customer_date::date
            FROM silver.orders

            UNION ALL

            SELECT order_estimated_delivery_date::date
            FROM silver.orders

            UNION ALL

            SELECT shipping_limit_date::date
            FROM silver.order_items
        ) dates
        WHERE event_date IS NOT NULL
    """

    bounds = pd.read_sql(query, engine)

    start_date = pd.to_datetime(bounds.loc[0, "min_date"])
    end_date = pd.to_datetime(bounds.loc[0, "max_date"])

    if pd.isna(start_date) or pd.isna(end_date):
        raise ValueError("No se encontraron fechas válidas.")

    if start_date > end_date:
        raise ValueError("El rango de fechas es inválido.")

    # Ampliar hasta los límites de cada año
    start_date = pd.Timestamp(
        year=start_date.year, month=1, day=1
    )

    end_date = pd.Timestamp(
        year=end_date.year, month=12, day=31
    )

    print(f"Fecha inicial: {start_date.date()}")
    print(f"Fecha final: {end_date.date()}")

    dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D"
    )

    df = pd.DataFrame({"full_date": dates})

    df["date_key"] = df["full_date"].dt.strftime(
        "%Y%m%d"
    ).astype("int64")

    df["day"] = df["full_date"].dt.day
    df["month"] = df["full_date"].dt.month
    df["quarter"] = df["full_date"].dt.quarter
    df["year"] = df["full_date"].dt.year

    df["day_of_week"] = (
        df["full_date"].dt.dayofweek + 1
    )

    df["month_name"] = df["month"].map(
        lambda m: MONTH_NAMES[m - 1]
    )

    df["day_name"] = df["day_of_week"].map(
        lambda d: DAY_NAMES[d - 1]
    )

    df["is_weekend"] = df["day_of_week"].isin([6, 7])

    # Convertir timestamp a fecha
    df["full_date"] = df["full_date"].dt.date

    expected_rows = len(df)

    if df["date_key"].duplicated().any():
        raise ValueError("Existen date_key duplicadas.")

    if df.isna().any().any():
        raise ValueError("Existen valores nulos.")

    print(f"Días generados: {expected_rows:,}")

    # Crear staging
    df.to_sql(
        "_dim_dates_loading",
        engine,
        schema="gold",
        if_exists="replace",
        index=False,
        chunksize=5000,
        dtype={
            "date_key": Integer(),
            "full_date": Date(),
            "day": Integer(),
            "month": Integer(),
            "month_name": String(20),
            "quarter": Integer(),
            "year": Integer(),
            "day_of_week": Integer(),
            "day_name": String(20),
            "is_weekend": Boolean(),
        }
    )

    # Publicación transaccional
    with engine.begin() as connection:

        connection.execute(
            text("TRUNCATE TABLE gold.dim_dates")
        )

        connection.execute(
            text("""
                INSERT INTO gold.dim_dates (
                    date_key,
                    full_date,
                    day,
                    month,
                    month_name,
                    quarter,
                    year,
                    day_of_week,
                    day_name,
                    is_weekend
                )
                SELECT
                    date_key,
                    full_date,
                    day,
                    month,
                    month_name,
                    quarter,
                    year,
                    day_of_week,
                    day_name,
                    is_weekend
                FROM gold._dim_dates_loading
                ORDER BY full_date
            """)
        )

        total = connection.execute(
            text("SELECT COUNT(*) FROM gold.dim_dates")
        ).scalar_one()

        if total != expected_rows:
            raise ValueError(
                "El total de fechas cargadas no coincide."
            )

        connection.execute(
            text(
                "DROP TABLE IF EXISTS "
                "gold._dim_dates_loading"
            )
        )

    print(f"Fechas cargadas en Gold: {total:,}")
    print("Tabla gold.dim_dates creada correctamente.")


def main():
    engine = get_engine()

    try:
        load_dim_dates(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

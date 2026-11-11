
from pathlib import Path
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
import os


# 1. Configuración

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "bronze" / "raw"

load_dotenv(PROJECT_ROOT / ".env")

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

DB_HOST = "localhost"
DB_PORT = 5433

SCHEMA = "bronze"
CHUNK_SIZE = 10000


# 2. Archivos y nombres de tablas

FILES = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "category_translation",
}


# 3. Crear conexión

def create_db_engine():

    if not all([DB_USER, DB_PASSWORD, DB_NAME]):
        raise ValueError(
            "Faltan credenciales de PostgreSQL en el archivo .env"
        )

    database_url = URL.create(
        "postgresql+psycopg",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

    return create_engine(database_url)


# --------------------------------------------------
# 4. Crear esquema Bronze
# --------------------------------------------------

def create_bronze_schema(engine):

    with engine.begin() as connection:
        connection.execute(
            text("CREATE SCHEMA IF NOT EXISTS bronze")
        )

    print("Esquema bronze preparado correctamente.")


# --------------------------------------------------
# 5. Cargar CSV por bloques
# --------------------------------------------------

def load_csv(engine, file_name, table_name):

    file_path = RAW_DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {file_path}"
        )

    print(f"\nCargando {file_name} -> {SCHEMA}.{table_name}")

    total_rows = 0
    first_chunk = True

    chunks = pd.read_csv(
        file_path,
        dtype=str,
        chunksize=CHUNK_SIZE
    )

    for chunk in chunks:

        chunk.to_sql(
            name=table_name,
            con=engine,
            schema=SCHEMA,
            if_exists="replace" if first_chunk else "append",
            index=False,
            chunksize=2000,
        )

        total_rows += len(chunk)
        first_chunk = False

        print(f"Filas cargadas: {total_rows:,}")

    print(f"Tabla completada: {table_name}")
    print(f"Total de filas: {total_rows:,}")

    return total_rows


# --------------------------------------------------
# 6. Ejecutar proceso
# --------------------------------------------------

def main():

    print("=" * 60)
    print("OLIST - DATA LOADING TO POSTGRESQL")
    print("=" * 60)

    if not RAW_DATA_DIR.exists():
        print(f"No existe la carpeta: {RAW_DATA_DIR}")
        sys.exit(1)

    engine = create_db_engine()

    results = {}
    errors = []

    try:

        # Verificar conexión
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("\nConexión a PostgreSQL exitosa.")

        create_bronze_schema(engine)

        for file_name, table_name in FILES.items():

            try:
                rows = load_csv(
                    engine,
                    file_name,
                    table_name
                )

                results[table_name] = rows

            except Exception as error:
                errors.append(
                    f"{file_name}: {error}"
                )

                print(f"ERROR: {error}")

        print("\n" + "=" * 60)
        print("RESUMEN DE CARGA")
        print("=" * 60)

        print(f"Tablas esperadas: {len(FILES)}")
        print(f"Tablas procesadas: {len(results)}")
        print(f"Errores: {len(errors)}")

        for table, rows in results.items():
            print(f"{table}: {rows:,} filas")

        if errors:
            print("\nErrores encontrados:")

            for error in errors:
                print(f"- {error}")

            sys.exit(1)

        print("\nCarga completada correctamente.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

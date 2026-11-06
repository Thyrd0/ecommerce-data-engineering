
from pathlib import Path
import json
import sys

import pandas as pd


# 1. Configuración de rutas

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "bronze" / "raw"
REPORT_DIR = PROJECT_ROOT / "docs"
REPORT_PATH = REPORT_DIR / "ingestion_report.json"



# 2. Archivos esperados

EXPECTED_FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


# 3. Inspeccionar un archivo CSV

def inspect_csv(file_path: Path) -> dict:

    print(f"\nProcesando: {file_path.name}")

    df = pd.read_csv(file_path)

    nulls_by_column = df.isnull().sum()

    report = {
        "file_name": file_path.name,
        "file_size_mb": round(file_path.stat().st_size / (1024 ** 2), 2),
        "total_rows": int(df.shape[0]),
        "total_columns": int(df.shape[1]),
        "columns": df.columns.tolist(),
        "data_types": {
            column: str(dtype)
            for column, dtype in df.dtypes.items()
        },
        "total_null_values": int(nulls_by_column.sum()),
        "nulls_by_column": {
            column: int(total)
            for column, total in nulls_by_column.items()
        },
        "duplicate_rows": int(df.duplicated().sum()),
    }

    print(f"Filas: {report['total_rows']:,}")
    print(f"Columnas: {report['total_columns']}")
    print(f"Valores nulos: {report['total_null_values']:,}")
    print(f"Filas duplicadas: {report['duplicate_rows']:,}")

    return report


# 4. Ejecutar proceso de inspección

def main():

    print("=" * 60)
    print("DATA INGESTION - OLIST DATASET")
    print("=" * 60)

    if not RAW_DATA_DIR.exists():
        print(f"ERROR: No existe la carpeta {RAW_DATA_DIR}")
        sys.exit(1)

    reports = []
    errors = []

    for file_name in EXPECTED_FILES:

        file_path = RAW_DATA_DIR / file_name

        if not file_path.exists():
            errors.append(f"No se encontró: {file_name}")
            continue

        try:
            report = inspect_csv(file_path)
            reports.append(report)

        except Exception as error:
            errors.append(f"Error en {file_name}: {error}")

    # Guardar reporte
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    final_report = {
        "dataset": "Brazilian E-Commerce Public Dataset by Olist",
        "total_expected_files": len(EXPECTED_FILES),
        "successfully_processed": len(reports),
        "total_errors": len(errors),
        "files": reports,
        "errors": errors,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            final_report,
            file,
            indent=4,
            ensure_ascii=False
        )

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN DE INGESTA")
    print("=" * 60)

    print(f"Archivos esperados: {len(EXPECTED_FILES)}")
    print(f"Archivos procesados: {len(reports)}")
    print(f"Errores: {len(errors)}")

    if errors:
        for error in errors:
            print(f"- {error}")

    print(f"\nReporte generado: {REPORT_PATH}")

    if errors:
        sys.exit(1)

    print("\nProceso completado correctamente.")


if __name__ == "__main__":
    main()

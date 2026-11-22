
# Olist E-commerce Data Warehouse

## 1. Objetivo

Implementar un Data Warehouse para analizar
información de comercio electrónico del dataset
Olist, utilizando una arquitectura Bronze,
Silver y Gold.

## 2. Arquitectura

### Bronze
Almacenamiento de los datos originales
procedentes de archivos CSV.

### Silver
Limpieza, normalización, tipado de datos
y validación de integridad referencial.

### Gold
Modelo dimensional para análisis de ventas,
pagos, clientes, productos, vendedores
y satisfacción del cliente.

## 3. Modelo dimensional

### Dimensiones

| Tabla | Registros | Clave primaria |
|---|---:|---|
| dim_customers | 99,441 | customer_key |
| dim_products | 32,951 | product_key |
| dim_sellers | 3,095 | seller_key |
| dim_dates | 1,827 | date_key |

### Tablas de hechos

| Tabla | Registros | Granularidad |
|---|---:|---|
| fact_order_items | 112,650 | Artículo por pedido |
| fact_order_payments | 103,886 | Registro de pago por pedido |
| fact_order_reviews | 99,224 | Reseña por pedido |

## 4. Relaciones

### fact_order_items
- customer_key -> dim_customers
- product_key -> dim_products
- seller_key -> dim_sellers
- date_key -> dim_dates

### fact_order_payments
- customer_key -> dim_customers
- date_key -> dim_dates

### fact_order_reviews
- customer_key -> dim_customers
- purchase_date_key -> dim_dates
- review_creation_date_key -> dim_dates
- review_answer_date_key -> dim_dates

## 5. Reglas de negocio

- Cada fila de fact_order_items representa
  un artículo de un pedido.
- Cada fila de fact_order_payments representa
  un registro de pago.
- Cada fila de fact_order_reviews representa
  una combinación única de review_id y order_id.
- Los productos sin categoría original
  se clasifican como "unknown".
- Los productos con categoría sin traducción
  se clasifican como "untranslated".
- Las fechas se representan mediante claves
  enteras con formato YYYYMMDD.
- Los importes de pagos no se suman directamente
  con los importes de artículos.

## 6. Validaciones

Auditoría Gold completada correctamente:

- Conteos Silver vs Gold: coincidentes.
- Integridad referencial: 0 errores.
- Claves naturales de dimensiones: únicas.
- Importes financieros: coincidentes.
- Tablas staging restantes: 0.

## 7. Indicadores disponibles

- Artículos vendidos o registrados.
- Pedidos distintos.
- Importe de artículos.
- Costos de envío.
- Importe de pagos.
- Métodos de pago.
- Calificación promedio.
- Distribución de reseñas.
- Evolución mensual de pedidos y pagos.

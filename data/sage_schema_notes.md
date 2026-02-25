# Sage/Peachtree (temp_sage_*) - notas de esquema y relaciones

Este documento resume la estructura observada en las tablas `temp_sage_*`, referencias publicas de Sage/Peachtree, y pruebas SQL ejecutadas contra la BD.

Fuentes publicas consultadas:
- https://dscorp.com/docs/sage-50-rest-server/sage-50-database-schemas/
- https://help-sage50.na.sage.com/en-us/2023/Content/DDFs/A_List_of_Data_Files.htm
- https://docs.zynk.com/workflow/developers/sage-50-uk-schema/index.html

## Contexto y caracteristicas del esquema Sage

- Sage 50 (Peachtree) usa un motor tipo Pervasive PSQL (Actian Zen) y un esquema plano y denormalizado.
- Las relaciones no suelen tener FKs; se infieren por campos tipo `RecordNumber`, `PostOrder`, `Journal`, etc.
- El mismo campo puede referir a entidades distintas segun el modulo (por ejemplo, `custvendid`).

## Mapa de tablas (equivalencias aproximadas)

- `temp_sage_chart` -> Chart of Accounts (CHART.DAT)
- `temp_sage_customers` -> Customers (CUSTOMER.DAT)
- `temp_sage_vendors` -> Vendors (VENDOR.DAT)
- `temp_sage_line_items` -> Inventory Items (LINEITEM.DAT)
- `temp_sage_jobs` -> Jobs/Projects (PROJECT.DAT)
- `temp_sage_journal_header` -> Journal Header (JRNLHDR.DAT)
- `temp_sage_journal_row` -> Journal Row (JRNLROW.DAT)
- `temp_sage_journal` -> Vista/tabla denormalizada (header + row + master data)

## Relaciones inferidas (observadas en esquema y pruebas)

1) Journal Header -> Journal Row
- `temp_sage_journal_header.jrnlkey_journal` + `postorder`
- `temp_sage_journal_row.journal` + `postorder`

2) Journal Header -> Customers / Vendors
- `temp_sage_journal_header.custvendid` se asocia a:
  - `temp_sage_customers.customerrecordnumber` (modulo Receivables)
  - `temp_sage_vendors.vendorrecordnumber` (modulo Payables)

3) Journal Row -> Items
- `temp_sage_journal_row.itemrecordnumber` -> `temp_sage_line_items.itemrecordnumber`
- No todas las filas tienen item (renglones de GL, taxes, etc.)

4) Journal Row -> Jobs
- `temp_sage_journal_row.jobrecordnumber` -> `temp_sage_jobs.jobrecordnumber`

5) Chart of Accounts / GL
- `temp_sage_chart.glacntnumber` aparece en:
  - `temp_sage_journal_row.glacntnumber` (cuenta por linea)
  - `temp_sage_journal_header.glacntnumber` (cuenta control)
  - `temp_sage_customers.glacntnumber` y `temp_sage_vendors.glacntnumber`

Nota: Varios `recordnumber` son `varchar` en masters y `int` en journal. Para joins suele requerirse `CAST`.

## Pruebas SQL ejecutadas

### Conteo de filas por tabla
```sql
SELECT 'temp_sage_chart' AS table_name, COUNT(*) AS rows_count FROM dbo.temp_sage_chart
UNION ALL SELECT 'temp_sage_customers', COUNT(*) FROM dbo.temp_sage_customers
UNION ALL SELECT 'temp_sage_jobs', COUNT(*) FROM dbo.temp_sage_jobs
UNION ALL SELECT 'temp_sage_journal_header', COUNT(*) FROM dbo.temp_sage_journal_header
UNION ALL SELECT 'temp_sage_journal_row', COUNT(*) FROM dbo.temp_sage_journal_row
UNION ALL SELECT 'temp_sage_line_items', COUNT(*) FROM dbo.temp_sage_line_items
UNION ALL SELECT 'temp_sage_vendors', COUNT(*) FROM dbo.temp_sage_vendors;
```

Resultados:
- temp_sage_chart: 2897
- temp_sage_customers: 5515
- temp_sage_jobs: 68218
- temp_sage_journal_header: 272819
- temp_sage_journal_row: 1962174
- temp_sage_line_items: 3174
- temp_sage_vendors: 7190

### Distribucion por modulo en journal_header
```sql
SELECT module, COUNT(*) AS rows_count
FROM dbo.temp_sage_journal_header
GROUP BY module
ORDER BY rows_count DESC;
```

Resultados:
- module P: 212941
- module R: 59878

### Cobertura custvendid -> customers/vendors (DISTINCT)
```sql
SELECT
  COUNT(DISTINCT h.id) AS total_headers,
  COUNT(DISTINCT CASE WHEN c.customerrecordnumber IS NOT NULL THEN h.id END) AS headers_with_customer,
  COUNT(DISTINCT CASE WHEN v.vendorrecordnumber IS NOT NULL THEN h.id END) AS headers_with_vendor
FROM dbo.temp_sage_journal_header h
LEFT JOIN dbo.temp_sage_customers c
  ON h.custvendid = c.customerrecordnumber
LEFT JOIN dbo.temp_sage_vendors v
  ON h.custvendid = v.vendorrecordnumber;
```

Resultados:
- total_headers: 272819
- headers_with_customer: 271357
- headers_with_vendor: 268968

Interpretacion: `custvendid` referencia clientes o proveedores segun modulo. La superposicion es esperable en un esquema sin FK.

### Cobertura itemrecordnumber -> line_items (DISTINCT)
```sql
SELECT
  COUNT(DISTINCT r.id) AS total_rows,
  COUNT(DISTINCT CASE WHEN li.itemrecordnumber IS NOT NULL THEN r.id END) AS rows_with_item
FROM dbo.temp_sage_journal_row r
LEFT JOIN dbo.temp_sage_line_items li
  ON CAST(r.itemrecordnumber AS varchar(50)) = li.itemrecordnumber;
```

Resultados:
- total_rows: 1962174
- rows_with_item: 871236

### Cobertura jobrecordnumber -> jobs (DISTINCT)
```sql
SELECT
  COUNT(DISTINCT r.id) AS total_rows,
  COUNT(DISTINCT CASE WHEN j.jobrecordnumber IS NOT NULL THEN r.id END) AS rows_with_job
FROM dbo.temp_sage_journal_row r
LEFT JOIN dbo.temp_sage_jobs j
  ON CAST(r.jobrecordnumber AS varchar(50)) = j.jobrecordnumber;
```

Resultados:
- total_rows: 1962174
- rows_with_job: 685550

## Recomendaciones de joins (para analisis)

1) Transacciones contables con detalle de lineas
```sql
SELECT h.*, r.*
FROM dbo.temp_sage_journal_header h
JOIN dbo.temp_sage_journal_row r
  ON h.jrnlkey_journal = r.journal
 AND h.postorder = r.postorder;
```

2) Transacciones + cliente/proveedor (segun modulo)
```sql
SELECT h.*, c.customerid, c.customer_bill_name, v.vendorid, v.name
FROM dbo.temp_sage_journal_header h
LEFT JOIN dbo.temp_sage_customers c
  ON h.custvendid = c.customerrecordnumber
LEFT JOIN dbo.temp_sage_vendors v
  ON h.custvendid = v.vendorrecordnumber;
```

3) Lineas + item
```sql
SELECT r.*, li.itemid, li.itemdescription
FROM dbo.temp_sage_journal_row r
LEFT JOIN dbo.temp_sage_line_items li
  ON CAST(r.itemrecordnumber AS varchar(50)) = li.itemrecordnumber;
```

4) Lineas + job
```sql
SELECT r.*, j.jobid, j.jobdescription
FROM dbo.temp_sage_journal_row r
LEFT JOIN dbo.temp_sage_jobs j
  ON CAST(r.jobrecordnumber AS varchar(50)) = j.jobrecordnumber;
```

## Diagrama ER (texto, aproximado)

```text
temp_sage_chart
  (glacntnumber)
        ^
        |
        |  (glacntnumber)
temp_sage_journal_row ----------------------- temp_sage_line_items
  (journal, postorder)                         (itemrecordnumber)
        ^
        |
        |  (journal, postorder)
temp_sage_journal_header
  (custvendid)
     /   \
    /     \
   v       v
temp_sage_customers         temp_sage_vendors
 (customerrecordnumber)      (vendorrecordnumber)

temp_sage_journal_row -------------- temp_sage_jobs
 (jobrecordnumber)                   (jobrecordnumber)
```

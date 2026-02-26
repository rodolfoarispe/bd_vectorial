# Análisis de Facturas por Job en Sage/Peachtree (temp_sage_*)

Este documento explica cómo extraer información de facturas agrupadas por job del sistema Sage/Peachtree, incluyendo el estado de pago y la clasificación entre ingresos y gastos.

## Contexto del problema

El objetivo es obtener un reporte que muestre:
- Facturas de un período específico (mes)
- Agrupadas por job/proyecto
- Con estado de pago (pendiente, pagada, parcial)
- Clasificadas como ingresos o gastos según el tipo de documento

## Estructura de datos relevante

### Tablas principales
- `temp_sage_journal_header`: Cabecera de transacciones contables
- `temp_sage_journal_row`: Líneas de detalle de transacciones
- `temp_sage_jobs`: Proyectos/trabajos
- `temp_sage_customers`: Clientes (para módulo R)
- `temp_sage_vendors`: Proveedores (para módulo P)

### Campos clave para facturas

#### En `temp_sage_journal_header`:
- **`module`**: Identifica el tipo de transacción
  - `'R'` = Receivables (Cuentas por Cobrar) → **FACTURAS A CLIENTES** → Ingresos
  - `'P'` = Payables (Cuentas por Pagar) → **FACTURAS DE PROVEEDORES** → Gastos

- **Identificación de facturas** (referencias cruzadas):
  - `reference`: Número de factura (documento principal - módulo R cliente, P proveedor)
  - `invnumforthistrx` (en journal_row): Referencia cruzada relacionada (PO, embarque, etc.)
  - ⚠️ `customerinvoiceno`: Casi nunca se usa (0.02%) - ignorar en nuevas queries

- **Montos**:
  - `mainamount`: Monto principal de la transacción
    - Módulo R: Positivo (ingresos)
    - Módulo P: Negativo (gastos)

- **Estado de pago**:
  - `amountpaid`: Monto pagado parcialmente
  - `totalinvoicepaid`: Indicador de pago completo (varchar que contiene el monto total cuando está pagada)

#### En `temp_sage_journal_row`:
- **`jobrecordnumber`**: Enlace con `temp_sage_jobs.jobrecordnumber`
- **`journal` + `postorder`**: Clave compuesta para enlazar con header

## Lógica de joins

### 1. Header ↔ Row (relación 1:N)
```sql
FROM temp_sage_journal_header h
JOIN temp_sage_journal_row r
  ON h.jrnlkey_journal = r.journal 
 AND h.postorder = r.postorder
```

**Razón**: Cada transacción contable tiene un header (cabecera) y múltiples rows (líneas de detalle). La clave compuesta `journal + postorder` garantiza la integridad relacional.

### 2. Row → Jobs (relación N:1)
```sql
LEFT JOIN temp_sage_jobs j
  ON CAST(r.jobrecordnumber AS varchar(50)) = j.jobrecordnumber
```

**Razón**: 
- No todas las líneas contables están asociadas a un job específico
- Se requiere `CAST` porque hay inconsistencia de tipos (`int` en row, `varchar` en jobs)
- Se usa `LEFT JOIN` para incluir transacciones sin job asignado

### 3. Filtros para facturas válidas
```sql
WHERE r.jobrecordnumber IS NOT NULL 
  AND r.jobrecordnumber <> 0
  AND h.mainamount <> 0
```

**Razón**:
- `jobrecordnumber IS NOT NULL AND <> 0`: Solo líneas asociadas a jobs
- `mainamount <> 0`: Excluye transacciones sin monto (ajustes, reclasificaciones)

## Lógica de estado de pago

### Estados definidos:
1. **PENDIENTE**: No hay pagos registrados
2. **PAGADA**: Pago completo registrado
3. **PARCIAL**: Pago parcial registrado

### Implementación:
```sql
CASE 
    WHEN TRY_CAST(h.totalinvoicepaid AS float) > 0 THEN 'PAGADA'
    WHEN h.amountpaid = 0 THEN 'PENDIENTE'
    WHEN ABS(h.amountpaid) >= ABS(h.mainamount) THEN 'PAGADA'
    ELSE 'PARCIAL'
END AS estado_pago
```

**Razón del orden:**
1. **`totalinvoicepaid > 0`** se evalúa primero porque es el indicador más confiable de pago completo
2. **`amountpaid = 0`** indica que no hay pagos parciales registrados
3. **`ABS(amountpaid) >= ABS(mainamount)`** maneja el caso donde el pago parcial equals o excede el monto
4. **`PARCIAL`** cubre todos los demás casos

**Nota sobre `TRY_CAST`**: 
- `totalinvoicepaid` es `varchar` y puede contener valores como `'0.0'`, `''`, o `NULL`
- `TRY_CAST` evita errores de conversión y devuelve `NULL` para valores no numéricos

## Clasificación Ingresos vs Gastos

### Lógica implementada:
```sql
CASE 
    WHEN h.module = 'R' THEN h.mainamount 
    ELSE 0 
END AS ingresos,
CASE 
    WHEN h.module = 'P' THEN ABS(h.mainamount) 
    ELSE 0 
END AS gastos
```

**Razón**:
- **Módulo R (Receivables)**: Facturas emitidas a clientes
  - `mainamount` es positivo por naturaleza
  - Se toma el valor directo como ingreso

- **Módulo P (Payables)**: Facturas recibidas de proveedores
  - `mainamount` es negativo por naturaleza contable
  - Se usa `ABS()` para convertir a positivo y mostrarlo como gasto

## Query completo con explicación

```sql
SELECT 
    j.jobid,
    j.jobdescription,
    COALESCE(h.reference, r.invnumforthistrx, 'SIN_FACTURA') AS factura,
    h.transactiondate AS fecha_factura,
    h.module,
    h.mainamount AS monto_factura,
    CASE 
        WHEN TRY_CAST(h.totalinvoicepaid AS float) > 0 THEN 'PAGADA'
        WHEN h.amountpaid = 0 THEN 'PENDIENTE'
        WHEN ABS(h.amountpaid) >= ABS(h.mainamount) THEN 'PAGADA'
        ELSE 'PARCIAL'
    END AS estado_pago,
    h.amountpaid,
    h.totalinvoicepaid,
    CASE 
        WHEN h.module = 'R' THEN h.mainamount 
        ELSE 0 
    END AS ingresos,
    CASE 
        WHEN h.module = 'P' THEN ABS(h.mainamount) 
        ELSE 0 
    END AS gastos
FROM dbo.temp_sage_journal_header h
JOIN dbo.temp_sage_journal_row r
    ON h.jrnlkey_journal = r.journal 
   AND h.postorder = r.postorder
LEFT JOIN dbo.temp_sage_jobs j
    ON CAST(r.jobrecordnumber AS varchar(50)) = j.jobrecordnumber
WHERE h.transactiondate >= '2026-12-01' 
  AND h.transactiondate < '2027-01-01'
  AND r.jobrecordnumber IS NOT NULL 
  AND r.jobrecordnumber <> 0
  AND h.mainamount <> 0
ORDER BY 
    j.jobid, 
    h.transactiondate DESC,
    h.id;
```

**Nota sobre COALESCE actualizado:**
- Se eliminó `customerinvoiceno` (casi nunca se usa, 0.02% de registros)
- Orden: `reference` (documento principal) → `invnumforthistrx` (referencia cruzada)
- Ver `data/analisis_numero_factura_sage.md` para detalles sobre referencias cruzadas

## Validaciones realizadas

### Cobertura de datos:
- **Total headers**: 272,819 transacciones
- **Headers con job válido**: ~685,550 líneas (35% del total)
- **Módulos identificados**: P (212,941), R (59,878)

### Estados de pago observados:
- **Módulo R**: 20,052 pendientes, 39,367 pagadas, 93 parciales
- **Módulo P**: 109,980 pendientes, 96,607 pagadas, 1,145 parciales

## Casos de uso adicionales

### Resumen por job (sin detalle de facturas):
```sql
SELECT 
    j.jobid,
    j.jobdescription,
    SUM(CASE WHEN h.module = 'R' THEN h.mainamount ELSE 0 END) AS total_ingresos,
    SUM(CASE WHEN h.module = 'P' THEN ABS(h.mainamount) ELSE 0 END) AS total_gastos,
    COUNT(CASE WHEN h.module = 'R' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) THEN 1 END) AS facturas_cobradas,
    COUNT(CASE WHEN h.module = 'P' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) THEN 1 END) AS facturas_pagadas
FROM dbo.temp_sage_journal_header h
JOIN dbo.temp_sage_journal_row r
    ON h.jrnlkey_journal = r.journal AND h.postorder = r.postorder
LEFT JOIN dbo.temp_sage_jobs j
    ON CAST(r.jobrecordnumber AS varchar(50)) = j.jobrecordnumber
WHERE h.transactiondate >= '2026-12-01' 
  AND h.transactiondate < '2027-01-01'
  AND r.jobrecordnumber IS NOT NULL 
  AND r.jobrecordnumber <> 0
  AND h.mainamount <> 0
GROUP BY j.jobid, j.jobdescription
ORDER BY j.jobid;
```

## Limitaciones y consideraciones

1. **Tipos de datos inconsistentes**: Requiere `CAST` para joins entre `recordnumber`
2. **Esquema denormalizado**: Sin FKs formales, las relaciones se infieren
3. **Estados de pago**: La lógica puede variar según la versión de Sage y configuración
4. **Filtros de fecha**: Usar patrón cerrado-abierto (`>= inicio AND < fin`)

## Referencias
- Ver `data/sage_schema_notes.md` para detalles del esquema general
- Documentación pública de Sage 50: https://dscorp.com/docs/sage-50-rest-server/sage-50-database-schemas/
# Análisis: Número de Factura en Sage - Campos `reference` vs `invnumforthistrx`

## Problema

El COALESCE actual en `vi_sage_jobs_facturas` asume un orden de prioridad:
```sql
COALESCE(h.reference, h.customerinvoiceno, r.invnumforthistrx, 'SIN_FACTURA') AS factura
```

Pero:
1. Los usuarios de Sage pueden usar AMBOS campos con significados diferentes
2. `customerinvoiceno` casi nunca se usa (0.03% de casos)
3. `reference` vs `invnumforthistrx` tienen diferencias semánticas en 51% de casos (Módulo P)

## Hallazgos de Consistencia

### Distribución de campos por módulo:

**Módulo P (Proveedores/Cuentas por Pagar):**
- Total registros: 498,931
- `reference` presente: 498,921 (99.98%)
- `customerinvoiceno` presente: 157 (0.03%) ← **CASI NUNCA**
- `invnumforthistrx` presente: 410,931 (82.34%)
- Ambos `reference` + `invnumforthistrx`: 410,927
  - Son IGUALES: 213,036 (48.9%)
  - Son DIFERENTES: 223,134 (51.1%)

**Módulo R (Clientes/Cuentas por Cobrar):**
- Total registros: 428,387
- `reference` presente: 428,339 (99.99%)
- `customerinvoiceno` presente: 0 (0%) ← **NUNCA**
- `invnumforthistrx` presente: 415,046 (96.87%)
- Ambos `reference` + `invnumforthistrx`: 415,046
  - Son IGUALES: 319,440 (75.8%)
  - Son DIFERENTES: 101,841 (24.2%)

## Interpretación

### Teoría sobre el significado:

**Para Módulo P (Proveedores):**
- `reference`: Número interno de GECA (ej: número de PO, referencia interna)
- `invnumforthistrx`: Número de factura **del proveedor** (lo que aparece en el documento físico)
- Casos donde son DIFERENTES (51%): El proveedor emite factura X pero GECA la identifica internamente como Y

**Para Módulo R (Clientes):**
- `reference`: Número de factura emitida por GECA al cliente
- `invnumforthistrx`: Campo alternativo (frecuentemente igual a reference)
- Casos donde son DIFERENTES (24%): Posiblemente transacciones de ajuste o notas de crédito

## Recomendación

### Opción 1: COALESCE Revisado (MENOS RECOMENDADO)
```sql
COALESCE(h.reference, r.invnumforthistrx, 'SIN_FACTURA') AS factura
```
**Cambio:** Eliminar `customerinvoiceno` (casi nunca se usa)

### Opción 2: Separar campos por contexto (RECOMENDADO)
```sql
SELECT 
    h.reference AS factura_numero_interno,
    r.invnumforthistrx AS factura_numero_proveedor,
    h.module,
    CASE 
        WHEN h.module = 'R' THEN COALESCE(h.reference, r.invnumforthistrx, 'SIN_FACTURA')
        WHEN h.module = 'P' THEN r.invnumforthistrx  -- Prioridad: número del proveedor
        ELSE 'SIN_FACTURA'
    END AS factura_numero_efectivo
FROM ...
```

### Opción 3: Mostrar ambos + indicador (PARA AUDITORÍA)
```sql
SELECT 
    h.reference AS ref_geca,
    r.invnumforthistrx AS ref_proveedor,
    CASE 
        WHEN h.reference = r.invnumforthistrx THEN 'CONSISTENTES'
        ELSE 'INCONSISTENTES' 
    END AS validacion_factura,
    ...
FROM ...
```

## Recomendación Final

**Para `vi_sage_jobs_facturas`:**

Mantener solo:
```sql
COALESCE(h.reference, r.invnumforthistrx, 'SIN_FACTURA') AS factura_numero
```

Pero agregar campos adicionales para auditoría:
```sql
h.reference AS factura_ref_geca,
r.invnumforthistrx AS factura_ref_proveedor,
CASE 
    WHEN h.reference <> r.invnumforthistrx THEN 'VERIFICAR'
    ELSE 'OK'
END AS flag_validacion_factura
```

Así los usuarios pueden:
1. Ver el número "efectivo" de factura (COALESCE)
2. Auditar si hay inconsistencias
3. Investigar casos donde reference != invnumforthistrx

## Notas técnicas

- `customerinvoiceno` se puede ignorar (solo 157 registros de 927,318)
- Para Módulo P: En 51% de casos `reference` ≠ `invnumforthistrx`
- Para Módulo R: En 24% de casos `reference` ≠ `invnumforthistrx`
- No se recomienda asumir orden de prioridad sin verificar contexto del usuario


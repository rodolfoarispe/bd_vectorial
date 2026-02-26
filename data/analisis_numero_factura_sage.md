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

## CONCLUSIÓN: Son Referencias Cruzadas, NO Duplicados

### Hallazgo Clave

Análisis de **cardinalidad** reveló que estos campos son **referencias cruzadas entre sistemas**, no duplicados o alternativas:

#### Módulo R (Clientes):
- `reference`: 54,782 valores únicos de 60,801 registros = **90.1% únicos**
  - Cada factura a cliente tiene número único
  - **Significado:** Número de factura emitida por GECA al cliente
  
- `invnumforthistrx`: 34,633 valores únicos de 421,286 registros = **8.2% únicos**
  - Muchas líneas reutilizan el mismo valor
  - **Significado:** Referencia cruzada a documento del cliente (PO, embarque, etc.)

#### Módulo P (Proveedores):
- `reference`: 115,783 valores únicos de 218,054 registros = **53.1% únicos**
  - Bastantes valores únicos (facturas de distintos proveedores)
  - **Significado:** Número de factura del proveedor (documento recibido)
  
- `invnumforthistrx`: 49,766 valores únicos de 436,178 registros = **11.4% únicos**
  - Muy pocos valores únicos (se reutilizan)
  - **Significado:** Referencia cruzada interna de GECA (PO generada, acta, etc.)

### Por qué "Casi siempre ambos están llenos"

Porque **son campos complementarios, no alternativos**:
- SIEMPRE hay referencia principal (factura o documento)
- SIEMPRE hay referencia cruzada (documento relacionado en otra parte del sistema)
- No hay confusión porque cumplen propósitos diferentes

## Recomendación Final (IMPLEMENTADA)

**Para `vi_sage_jobs_facturas`:**

```sql
COALESCE(h.reference, r.invnumforthistrx, 'SIN_FACTURA') AS factura
```

**Justificación:**
1. `customerinvoiceno` se puede ignorar (prácticamente nunca se usa)
2. Siempre hay al menos uno de los dos campos
3. `reference` es el número de factura efectivo (prioridad)
4. `invnumforthistrx` es fallback para casos raros donde `reference` esté vacío
5. No hay ambigüedad: son referencias cruzadas, no alternativas

**Cambios implementados:**
- ✅ Eliminado `customerinvoiceno` del COALESCE
- ✅ Mantenido orden: `reference` → `invnumforthistrx` → 'SIN_FACTURA'
- ✅ Agregado campo `company_name` al inicio de la vista
- ✅ Vista `vi_sage_jobs_facturas` actualizada en producción

## Notas técnicas

- **`customerinvoiceno`**: 157 de 927,318 registros (0.02%) - prácticamente inútil
- **Diferencias semánticas son ESPERADAS**: 51% en P, 24% en R (propósito diferente de cada campo)
- **Cobertura prácticamente completa**: ~99.99% en ambos campos combinados
- **Referencias cruzadas**: Son el sistema de GECA para vincular documentos entre módulos R y P
- **Orden de prioridad**: `reference` es el documento principal (factura emitida/recibida)


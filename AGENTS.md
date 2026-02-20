# Instrucciones: SQL desde Documentación Vectorial

## Visión General

Este sistema permite construir consultas SQL confiables usando una estrategia **híbrida**:
- **Búsqueda semántica** para encontrar conceptos, reglas de negocio y relaciones
- **Búsqueda literal** para obtener esquemas exactos sin ambigüedades

El objetivo es evitar asumir o "alucinar" nombres de campos o tipos de datos.

---

## Sistemas Integrados en GECA

**IMPORTANTE:** El proyecto GECA integra DOS SISTEMAS SEPARADOS:

### 1. **Magaya** (Sistema de Manejo de Carga / Logistics)
Tablas documentadas:
- `temp_shipment_master` - Embarques
- `temp_shipment_charges` - Cargos del embarque
- `temp_shipment_items` - Items del embarque
- `temp_accounting_master` - Documentos financieros (Bills, Invoices)
- `temp_accounting_charges` - Cargos contables del documento

**Flujo:** Embarque → Cargos → Documento Financiero → Cargos Contables

### 2. **Peachtree/Sage** (Sistema de Contabilidad / Accounting)
Tablas (NO DOCUMENTADAS - referencias informativas):
- `temp_sage_chart` - Catálogo de cuentas de Sage
- `temp_sage_*` - Otras tablas del sistema contable

**Nota:** Las tablas `temp_sage_*` son un sistema separado y NO tienen relación directa con las tablas Magaya. Son dos sistemas paralelos que conviven en la misma BD.

---

## Orden Jerárquico de Búsqueda

Usa esta jerarquía para obtener información sin ir innecesariamente a la BD:

**1. Caché de Esquemas** (`data/schemas_cache.json`)
   - ✅ Consulta **primero aquí** para nombres de columnas exactos y tipos de datos
   - ✅ Búsqueda literal, sin ambigüedad, disponible localmente
   - Comando: `main.py schema <tabla>`
   - Ejemplo: `main.py schema temp_shipment_charges`

**2. Documentación Vectorial** (`data/proyectos_documentacion.csv`)
   - ✅ Usa aquí para entender relaciones entre entidades, reglas de negocio y contexto
   - ✅ Búsqueda semántica para conceptos y lógica
   - Comando: `main.py search "<pregunta>"`
   - Ejemplo: `main.py search "como se relacionan cargos con embarques"`

**3. Base de Datos Directa**
   - ✅ Usa aquí **solo cuando necesites** valores concretos, datos vivos o auditoría
   - Ejemplo: Obtener distintos valores de una dimensión, contar registros, validar datos en vivo

**Caso típico:**
1. `main.py schema temp_shipment_charges` → Obtén columnas exactas
2. `main.py search "ChargeDefinitionAccountDefinitionType significado"` → Entiende qué significa
3. Consulta BD si necesitas valores específicos o datos vivos

**Caso especial - Tablas de Sage:**
- Si necesitas información de `temp_sage_*` (contabilidad Sage), consulta **directamente la BD**
- NO están documentadas en la BD vectorial (son sistema separado)
- Ejemplo: Obtener mapeo de accountid a tipos contables desde `temp_sage_chart`

---

## Flujo de Trabajo

### Paso 1: Buscar contexto y conceptos (Semántica)

Cuando necesites entender relaciones entre entidades o reglas de negocio, usa búsqueda vectorial:

```bash
/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos search "<pregunta>" -n 5
```

**Ejemplos:**
- `search "como se relacionan los cargos con los embarques"`
- `search "que campos definen un cargo"`
- `search "cual es la diferencia entre Status y Estado"`

Esto devuelve documentos del CSV con contexto, catálogos y relaciones.

### Paso 2: Consultar esquemas exactos (Literal)

Cuando necesites columnas, tipos de datos o validar que un campo existe, usa búsqueda literal:

```bash
/home/rodolfoarispe/vEnv/mem0/bin/python main.py schema <tabla>
```

**Ejemplos:**
- `main.py schema temp_shipment_charges` → lista todas las columnas y tipos
- `main.py schema temp_shipment_items` → esquema completo sin ambigüedad

**Regla de oro:** NUNCA asumas un nombre de campo. Siempre consulta el esquema primero.

### Paso 3: Construir y ejecutar SQL

Con la información de los pasos 1 y 2, construye la consulta SQL:
- Usa los campos exactos del esquema (paso 2)
- Respeta las relaciones documentadas (paso 1)
- Para rangos de fechas: cerrado-abierto (`>= inicio AND < fin`)

Ejecuta contra la BD usando la conexión `sql_enrich` configurada en `collections.yaml`.

Devuelve:
- El SQL exacto que ejecutaste
- Los resultados obtenidos

---

## Ambiente Python

Toda ejecución de comandos debe usar:

```
/home/rodolfoarispe/vEnv/mem0/bin/python
```

Si el venv no existe, recréalo siguiendo las instrucciones en `requirements.txt`.

---

## Sincronización de Esquemas

El caché de esquemas (`data/schemas_cache.json`) se **genera automáticamente** cuando indexas la colección:

```bash
/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos index --clear
```

**Proceso automático:**
1. Lee todas las tablas mencionadas en `data/proyectos_documentacion.csv`
2. Consulta `sql_enrich` para obtener columnas y tipos de cada tabla
3. Almacena en JSON (sin embeddings, búsqueda literal)

Cuando modifiques el CSV (añadas nuevas tablas), simplemente reindexea y el caché se actualiza.

---

## Reglas Obligatorias

1. **Nunca asumas nombres de campos** → Siempre consulta `main.py schema <tabla>`
2. **Nunca uses tablas no documentadas** → Verifica que aparezcan en `main.py schema <tabla>`
3. **Para rangos de fechas** → Usa sintaxis cerrado-abierto: `>= '2025-01-01' AND < '2025-01-31'`
4. **Si un campo no aparece en el esquema** → No lo uses. Pregunta o busca en el contexto.

---

## Documentación Disponible

### Documentadas (Sistema Magaya)
- **data/proyectos_documentacion.csv** → Documentación completa del sistema de embarques y logística
  - temp_shipment_master
  - temp_shipment_charges
  - temp_shipment_items
  - temp_accounting_master
  - temp_accounting_charges

- **data/schemas_cache.json** → Caché literal de esquemas (auto-generado)
  - Contiene todos los campos exactos de las 5 tablas Magaya

### Referencias (Sistema Sage)
- **temp_sage_chart** - Catálogo de cuentas Sage
- Otras tablas `temp_sage_*` - Sistema contable Peachtree
- **Consultar directamente en BD:** No están documentadas en la vectorial (sistema separado)

### Otros
- **GUIA.md** → Cómo funciona el sistema de búsqueda vectorial y enriquecimiento
- **collections.yaml** → Configuración de colecciones, fuentes, credenciales, sql_enrich

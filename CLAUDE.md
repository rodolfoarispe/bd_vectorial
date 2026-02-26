# CLAUDE.md — bd_vectorial

Sistema híbrido para análisis de datos de GECA: búsqueda semántica (ChromaDB + Ollama) sobre documentación de negocio + consultas SQL directas contra MSSQL (sistemas Magaya y Sage/Peachtree).

## Archivos de documentación y cuándo usarlos

### AGENTS.md — Instrucciones del asistente IA
**Leer primero al comenzar una sesión nueva.**
Contiene el flujo de trabajo completo para construir consultas SQL: jerarquía de búsqueda (caché → vectorial → BD), reglas obligatorias (nunca asumir nombres de campos), protocolo de seguridad para producción, descripción de los dos sistemas (Magaya y Sage), y referencia a todos los archivos del proyecto.

### DDL_EXECUTOR.md — Operaciones DDL seguras
Consultar cuando el usuario pida **modificar la estructura** de la base de datos (crear/alterar/eliminar vistas o tablas).
- Herramienta segura con confirmación explícita
- Solo se invoca cuando el usuario lo pide
- Auditoría completa de operaciones
- Protecciones contra operaciones peligrosas

### GUIA.md — Documentación técnica del sistema vectorial
Consultar cuando necesites entender o modificar la arquitectura del sistema (ChromaDB, Ollama, colecciones).
- Comandos CLI (`main.py index`, `search`, `schema`, `stats`)
- Cómo agregar conocimiento nuevo (CSV + reindexar)
- Qué campos vectorizar vs. dejar como metadata
- Cómo mover el proyecto a otra máquina

### CONEXION_PRODUCCION.md — Conexión a GECA producción
Consultar cuando el usuario necesite trabajar contra el servidor de producción.
- Script automatizado: `./scripts/geca_prod.sh start/stop/status`
- Proceso manual (respaldo): túnel SSH + VPN
- **El script debe ejecutarse manualmente por el usuario — nunca automáticamente**

### data/sage_schema_notes.md — Esquema Sage/Peachtree
Consultar cuando escribas queries sobre tablas `temp_sage_*`.
- Mapa de tablas (equivalencias con archivos .DAT de Sage 50)
- Relaciones inferidas entre journal_header, journal_row, jobs, customers, vendors
- Diagrama ER textual
- SQLs de prueba ejecutados con resultados reales

### data/sage_facturas_jobs_analisis.md — Facturas por job (Sage)
Consultar cuando el usuario pida reportes de facturas agrupadas por job/proyecto.
- Lógica de estado de pago (PENDIENTE / PAGADA / PARCIAL)
- Clasificación ingresos vs. gastos (módulo R vs. P)
- Query completo listo para adaptar
- Casos de uso: detalle por factura y resumen por job

## Archivos de configuración

| Archivo | Propósito |
|---|---|
| `collections.yaml` | Colecciones, fuentes de datos, conexiones, sql_enrich |
| `collections.secrets.yaml` | Credenciales de BD (no versionar, chmod 600) |
| `data/proyectos_documentacion.csv` | Fuente de verdad del conocimiento de negocio (Magaya) |
| `data/schemas_cache.json` | Caché de esquemas auto-generado al indexar |

## Entorno Python

```bash
PYTHON=/home/rodolfoarispe/vEnv/mem0/bin/python
```

Ollama debe estar corriendo (`ollama serve`) con modelos `nomic-embed-text` y `qwen2.5-coder:3b`.

## Protocolo para el asistente IA

**IMPORTANTE:** Cuando recibas una tarea de consulta, SIEMPRE sigue este orden:

### Paso 1: Descubrimiento (leer documentación)
1. **Leer CLAUDE.md** (este archivo) - Identifica qué documento especializado necesitas
2. **Leer documento especializado** basado en la tarea:
   - ¿Conexión a producción? → CONEXION_PRODUCCION.md
   - ¿Consulta SQL? → AGENTS.md (sección "Paso 3: Ejecutar SQL")
   - ¿Entender tablas Sage? → data/sage_schema_notes.md
   - ¿Entender tablas Magaya? → data/proyectos_documentacion.csv

### Paso 2: Validación (verificar prerequisitos)
1. **¿Qué ambiente necesita?**
   - Desarrollo: usa `-c proyectos`
   - Producción: usuario debe ejecutar `./scripts/geca_prod.sh start` primero

2. **¿Qué tabla/vista necesita?**
   - Ejecuta: `main.py schema <tabla>` para obtener esquema exacto

3. **¿Qué contexto de negocio necesita?**
   - Ejecuta: `main.py search "<tema>"` para entender relaciones

### Paso 3: Ejecución (solo después de validar)
- Ejecuta SQL con `main.py -c proyectos_prod sql "<query>"` o `query_prod.py "<query>"`

### Ejemplo de flujo correcto:

**Tarea:** "Muéstrame vistas con 'sage' en producción"

```
1. DESCUBRIMIENTO:
   ├─ Leer CLAUDE.md ← "Es consulta a producción"
   ├─ Leer CONEXION_PRODUCCION.md ← "Debo validar túnel"
   └─ Leer AGENTS.md Paso 3 ← "Debo usar main.py sql"

2. VALIDACIÓN:
   ├─ Usuario ejecutó: ./scripts/geca_prod.sh start ✓
   └─ Verificar túnel: ./scripts/geca_prod.sh status ✓

3. EJECUCIÓN:
   └─ main.py -c proyectos_prod sql "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='VIEW' AND TABLE_NAME LIKE '%sage%'"
```

## Reglas críticas

1. **Nunca asumir nombres de campos** → siempre consultar `main.py schema <tabla>`
2. **Producción** → recordar al usuario ejecutar manualmente `./scripts/geca_prod.sh start`; solo SELECT salvo indicación contraria
3. **Tablas Sage** (`temp_sage_*`) → no están en la BD vectorial; consultar directamente la BD o `data/sage_schema_notes.md`
4. **Tablas Magaya** → usar jerarquía: caché de esquemas → búsqueda vectorial → BD directa
5. **LEER DOCUMENTACIÓN PRIMERO** → antes de intentar cualquier comando, consulta CLAUDE.md para mapear qué leer

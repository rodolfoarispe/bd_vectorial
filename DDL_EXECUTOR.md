# DDL Executor - Operaciones DDL Seguras

## Descripción

`ddl_executor.py` es una herramienta **segura** para ejecutar operaciones DDL (Data Definition Language) en producción.

**Características:**
- ✅ Requiere confirmación explícita ANTES de cada operación
- ✅ Muestra el SQL a ejecutar con números de línea
- ✅ Valida que sea operación permitida (no deja hacer DELETE, TRUNCATE, etc.)
- ✅ Registra TODAS las operaciones en log (auditoría)
- ✅ Solo se invoca cuando el usuario lo pide explícitamente

---

## Operaciones Soportadas

### ✅ Permitidas:
- `ALTER VIEW` - Modificar vistas
- `CREATE VIEW` - Crear nuevas vistas
- `DROP VIEW` - Eliminar vistas
- `ALTER TABLE` - Modificar tablas
- `CREATE TABLE` - Crear tablas

### ❌ Prohibidas (por seguridad):
- `DROP DATABASE`
- `TRUNCATE`
- `DELETE FROM`
- `INSERT INTO`
- `UPDATE`

---

## Uso

### Ejecutar SQL desde línea de comandos

```bash
/home/rodolfoarispe/vEnv/mem0/bin/python ddl_executor.py \
  -c proyectos_prod \
  --sql "ALTER VIEW dbo.vi_sage_jobs_facturas AS SELECT ..."
```

### Ejecutar SQL desde archivo

Crea un archivo `cambios.sql`:
```sql
ALTER VIEW dbo.vi_sage_jobs_facturas AS
SELECT 
    h.Company_Name AS company_name,
    -- resto del SQL...
FROM ...
```

Luego ejecuta:
```bash
/home/rodolfoarispe/vEnv/mem0/bin/python ddl_executor.py \
  -c proyectos_prod \
  --file cambios.sql
```

---

## Flujo de Confirmación

### 1. Mostrar operación
```
⚠️  ADVERTENCIA: Operación DDL en PRODUCCIÓN
===============================================

Colección: proyectos_prod

SQL a ejecutar:
    1 | ALTER VIEW dbo.vi_sage_jobs_facturas AS
    2 | SELECT
    ...
```

### 2. Advertencias
```
===============================================

⚠️  ESTA OPERACIÓN MODIFICA LA ESTRUCTURA DE LA BASE DE DATOS
   • No se puede deshacer automáticamente
   • Afectará a todos los usuarios de la BD
   • Será registrada en auditoría
```

### 3. Confirmación Explícita
```
¿Ejecutar esta operación? (escribir 'CONFIRMO' para continuar): CONFIRMO
```

El usuario DEBE escribir exactamente `CONFIRMO` (no basta con "sí" o Enter).

### 4. Ejecución y Log
```
⏳ Ejecutando operación DDL...
✅ Operación completada exitosamente
📝 Registrado en: ./logs/ddl_operations.log
```

---

## Auditoría: Archivo de Log

Todas las operaciones se registran en `logs/ddl_operations.log`:

```json
{"timestamp": "2026-02-25T20:15:30.123456", "collection": "proyectos_prod", "status": "SUCCESS", "operation": "ALTER VIEW dbo.vi_sage_jobs_facturas AS SELECT h.Company_Name AS company_name, ...", "error": null}
{"timestamp": "2026-02-25T20:16:45.654321", "collection": "proyectos_prod", "status": "FAILED", "operation": "DROP DATABASE analitica", "error": "Operación NO permitida"}
```

**Campos:**
- `timestamp` - Cuándo se ejecutó
- `collection` - Qué colección
- `status` - SUCCESS o FAILED
- `operation` - Primeros 100 caracteres del SQL
- `error` - Mensaje de error (si falló)

Ver el log:
```bash
tail -f logs/ddl_operations.log
```

---

## Ejemplos Prácticos

### Ejemplo 1: Agregar campo a vista

```bash
/home/rodolfoarispe/vEnv/mem0/bin/python ddl_executor.py \
  -c proyectos_prod \
  --sql "ALTER VIEW dbo.vi_sage_jobs_facturas AS SELECT h.Company_Name AS company_name, ... FROM ..."
```

### Ejemplo 2: Crear nueva vista

```bash
cat > /tmp/nueva_vista.sql << 'EOF'
CREATE VIEW dbo.vi_new_report AS
SELECT 
    company_name,
    SUM(monto_factura) as total
FROM dbo.vi_sage_jobs_facturas
GROUP BY company_name
EOF

/home/rodolfoarispe/vEnv/mem0/bin/python ddl_executor.py \
  -c proyectos_prod \
  --file /tmp/nueva_vista.sql
```

---

## Seguridad

### Validaciones incorporadas:

1. **Validar colección existe** - Si no existe la colección, falla
2. **Validar operación permitida** - Solo DDL de estructura (no datos)
3. **Validar sintaxis** - El SQL debe ser correcto
4. **Confirmación explícita** - Usuario debe escribir "CONFIRMO"
5. **Auditoría completa** - Todas las operaciones se registran

### Protecciones contra:
- ❌ Eliminar datos sin querer (`DELETE`, `TRUNCATE`)
- ❌ Eliminar base de datos completa (`DROP DATABASE`)
- ❌ Modificar datos (`INSERT`, `UPDATE`)
- ❌ Operaciones silenciosas (requiere confirmación manual)

---

## Integración con el Protocolo

Este executor se invoca **SOLO cuando:**
1. ✅ El usuario lo pide explícitamente
2. ✅ Se necesita modificar estructura (vistas, tablas, etc.)
3. ✅ No es parte del flujo automático

**No se usa en:**
- ❌ Consultas SELECT normales
- ❌ Validaciones de prerequisitos
- ❌ Operaciones de rutina

---

## Troubleshooting

### "Colección no encontrada"
```
❌ Colección 'proyectos_prod' no encontrada
```
**Solución:** Verifica el nombre de la colección en `collections.yaml`

### "Operación NO permitida"
```
❌ Operación NO permitida
   Operaciones soportadas: ALTER/CREATE/DROP VIEW, ALTER/CREATE TABLE
```
**Solución:** La operación que intentas no es permitida. Ver lista arriba.

### "Error al ejecutar operación"
```
❌ Error al ejecutar operación: ...
📝 Error registrado en: ./logs/ddl_operations.log
```
**Solución:** Ver el log para detalles del error

---

## Mejores Prácticas

1. **Siempre leer el SQL que se muestra** antes de escribir CONFIRMO
2. **Hacer backup** de la BD antes de operaciones grandes
3. **Probar en desarrollo primero** si es posible
4. **Registrar cambios** en documentación cuando modifiques vistas
5. **Revisar logs** periódicamente para auditoría

---

## Notas para Administradores

- Todos los cambios quedan registrados en `logs/ddl_operations.log`
- El log es acumulativo (no se borra)
- Para auditoría: parsear JSON del log
- El executor no tiene límites de operaciones (por diseño)
- Cambios persisten en la BD (no hay rollback automático)


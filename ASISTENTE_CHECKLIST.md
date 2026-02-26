# Checklist: Protocolo para Asistente IA

Este documento define el orden EXACTO que debe seguir el asistente antes de ejecutar cualquier comando.

> **REGLA FUNDAMENTAL:** Si no sigo este checklist paso a paso, probablemente cometeré errores.

---

## Checklist: Consulta SQL a BD

### ✅ Fase 1: DESCUBRIMIENTO (Leer Documentación)

- [ ] **Paso 1.1:** Leo CLAUDE.md líneas 55-70 (índice de archivos)
  
- [ ] **Paso 1.2:** Identifico qué tipo de tarea es:
  - [ ] ¿Es sobre conexión a producción? → Ir a 1.3
  - [ ] ¿Es consulta SQL general? → Ir a 1.4
  - [ ] ¿Es entender tablas Sage? → Ir a 1.5

- [ ] **Paso 1.3:** Leo CONEXION_PRODUCCION.md (si es producción)
  - [ ] Anoto: IP servidor (`192.168.1.11:1414`)
  - [ ] Anoto: Credenciales (`analitica / biuser20!`)
  - [ ] Anoto: Script de conexión (`./scripts/geca_prod.sh start`)
  - [ ] Anoto: Cómo verificar (`./scripts/geca_prod.sh status`)

- [ ] **Paso 1.4:** Leo AGENTS.md sección "Paso 3: Ejecutar SQL" 
  - [ ] Anoto: Comando development (`main.py -c proyectos sql`)
  - [ ] Anoto: Comando producción (`main.py -c proyectos_prod sql`)
  - [ ] Anoto: Script alternativo (`query_prod.py`)
  - [ ] Anoto: Límite por defecto (100 filas)

- [ ] **Paso 1.5:** Si es sobre Sage, leo data/sage_schema_notes.md
  - [ ] Anoto: Tablas disponibles (journal_header, journal_row, etc.)
  - [ ] Anoto: Relaciones principales

---

### ✅ Fase 2: VALIDACIÓN (Verificar Prerequisitos)

- [ ] **Paso 2.1:** Verifico AMBIENTE
  - [ ] ¿Desarrollo o producción? Especificar: ___________
  - [ ] ¿Colección a usar? `-c proyectos` o `-c proyectos_prod`

- [ ] **Paso 2.2:** Si es PRODUCCIÓN, verifico conexión
  - [ ] ¿El usuario ejecutó `./scripts/geca_prod.sh start`? 
    - [ ] SÍ → Continuar
    - [ ] NO → Recordar al usuario y esperar
  - [ ] Ejecuto: `./scripts/geca_prod.sh status`
    - [ ] ¿Muestra "OK"? → Continuar
    - [ ] ¿Muestra error? → NO continuar sin fijar

- [ ] **Paso 2.3:** Identifico TABLA/VISTA necesaria
  - [ ] ¿Está documentada? Especificar: ___________
  - [ ] Ejecuto: `main.py schema <tabla>` (para obtener esquema exacto)
  - [ ] Anoto columnas disponibles

- [ ] **Paso 2.4:** Si necesito CONTEXTO de negocio
  - [ ] Ejecuto: `main.py search "<tema>"` (para entender relaciones)
  - [ ] Anoto conceptos y reglas clave

- [ ] **Paso 2.5:** Verifico COMANDO correcto
  - [ ] ¿Qué comando usar?
    - [ ] `main.py -c proyectos_prod sql` (recomendado para prod)
    - [ ] `query_prod.py` (alternativo)
  - [ ] ¿Qué limite de filas? Default: 100 (o especificar: ___)

---

### ✅ Fase 3: CONSTRUCCIÓN SQL

- [ ] **Paso 3.1:** Construyo SQL usando información verificada
  - [ ] Uso SOLO campos del esquema (paso 2.3)
  - [ ] Respeto relaciones documentadas (paso 2.4)
  - [ ] Sigo reglas de fechas cerrado-abierto: `>= '2025-01-01' AND < '2025-01-02'`

- [ ] **Paso 3.2:** Valido SQL antes de ejecutar
  - [ ] ¿SELECT? (no INSERT/UPDATE/DELETE)
  - [ ] ¿Todos los campos existen?
  - [ ] ¿Sintaxis correcta?

---

### ✅ Fase 4: EJECUCIÓN

- [ ] **Paso 4.1:** Ejecuto comando
  ```bash
  main.py -c proyectos_prod sql "SELECT ..."
  # O alternativa:
  query_prod.py "SELECT ..." --limit 100
  ```

- [ ] **Paso 4.2:** Reporto resultados al usuario
  - [ ] Número de filas
  - [ ] Datos relevantes
  - [ ] Si hay límite alcanzado

---

## Checklist: Búsqueda Semántica

### ✅ Cuando usuario pide "Busca información sobre..."

- [ ] Leo AGENTS.md sección "Paso 1: Buscar contexto"
- [ ] Ejecuto: `main.py search "<pregunta>"`
- [ ] Anoto resultados (tabla, campos, contexto)
- [ ] Si necesito más detalle → buscar nuevamente con otra pregunta

---

## Checklist: Entender Tablas/Esquema

### ✅ Cuando usuario pide "¿Cuál es el esquema de...?"

- [ ] Ejecuto: `main.py schema <nombre_tabla>`
- [ ] Reporto TODAS las columnas y tipos
- [ ] Si tabla no existe → listo tablas disponibles

---

## Errores Comunes y Cómo Prevenirlos

| Error | Causa | Prevención |
|-------|-------|-----------|
| "Comando no encontrado" | No leí qué comandos existen | PASO 1.4: Leo AGENTS.md Paso 3 |
| "Túnel no activo" | No validé conexión | PASO 2.2: Ejecuto status |
| "Tabla no existe" | Asumí nombre de campo | PASO 2.3: main.py schema |
| "Query sin respuestas" | Columna no existe | PASO 2.3: Verifico esquema |
| "Conexión colgada" | No verifiqué prerequisitos | PASO 2: Toda la fase 2 |

---

## Ejemplo: Ejecución Correcta Paso a Paso

**Tarea:** "¿Cuáles son todas las vistas en producción que mencionan 'sage'?"

### Fase 1: DESCUBRIMIENTO
```
1.1 ✓ Leí CLAUDE.md
1.2 ✓ Identifico: Es SQL + Producción
1.3 ✓ Leí CONEXION_PRODUCCION.md → Túnel en localhost:1414
1.4 ✓ Leí AGENTS.md Paso 3 → Usar "main.py -c proyectos_prod sql"
```

### Fase 2: VALIDACIÓN
```
2.1 ✓ Ambiente: Producción
2.2 ✓ Conexión: Usuario ejecutó start, status = OK
2.3 ✓ Tabla: INFORMATION_SCHEMA.TABLES (sistema)
2.4 ✓ No necesito contexto semántico
2.5 ✓ Comando: main.py -c proyectos_prod sql, límite: 100
```

### Fase 3: CONSTRUCCIÓN SQL
```
SELECT TABLE_SCHEMA, TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'VIEW' 
AND LOWER(TABLE_NAME) LIKE '%sage%'
ORDER BY TABLE_NAME
```
✓ Valido: Es SELECT, sintaxis correcta

### Fase 4: EJECUCIÓN
```bash
/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos_prod sql \
  "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'VIEW' AND LOWER(TABLE_NAME) LIKE '%sage%' ORDER BY TABLE_NAME"
```

---

## Cuándo Preguntar vs. Cuándo Asumir

### ❓ PREGUNTAR al usuario si:
- No está claro si es desarrollo o producción
- No sé qué tabla específica busca
- Necesito límite de filas diferente a 100
- Voy a hacer INSERT/UPDATE/DELETE (salvo indicación explícita)

### ✅ ASUMIR (porque está documentado) si:
- Columnas exactas (ya las leí en `main.py schema`)
- Reglas de negocio (ya las leí en búsqueda semántica)
- Sintaxis SQL (es estándar)
- Límite = 100 filas (es el default documentado)

---

## Notas de Implementación

Este checklist debe:
- [ ] Estar visible al iniciar sesión
- [ ] Ser consultable cuando hay duda ("¿Cuál es el protocolo para...?")
- [ ] Validarse antes de ejecutar comandos arriesgados (SQL en producción)


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

## Servidores GECA

### **Servidor de Desarrollo/Analítica** (Configuración actual)
- **IP:** `192.168.0.14:1433`
- **Base de datos:** `analitica` 
- **Credenciales:** `sa / nvoThund3r25!`
- **Acceso:** Directo desde red local
- **Uso:** Desarrollo, análisis, sistema de BD vectorial

### **Servidor de Producción GECA**
- **IP Interna:** `192.168.1.11:1414`
- **Credenciales:** `analitica / biuser20!`
- **Base de datos:** `analitica`
- **Acceso:** Túnel SSH + VPN

#### **Proceso de conexión a Producción:**

**MÉTODO AUTOMÁTICO (Recomendado):**
```bash
# Conectar (script pedirá contraseña interactivamente)
./scripts/geca_prod.sh start

# Usar
/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos_prod schema <tabla>

# Desconectar (cierra túnel y VPN)
./scripts/geca_prod.sh stop
```

**COMANDOS DISPONIBLES:**
- `./scripts/geca_prod.sh start` - Conectar todo
- `./scripts/geca_prod.sh stop` - Desconectar todo
- `./scripts/geca_prod.sh status` - Ver estado
- `./scripts/geca_prod.sh force-stop` - Forzar cierre
- `./scripts/geca_prod.sh test` - Probar BD

**MÉTODO MANUAL (Solo si script falla):**
```bash
# Activar VPN + túnel
sshpass -p "Bichito21$" ssh rodolfoarispe@192.168.0.229 "scutil --nc start 'VPN'"
sshpass -p "Bichito21$" ssh -L 1414:192.168.1.11:1414 rodolfoarispe@192.168.0.229 -N &

# Desconectar
pkill -f "ssh.*1414.*192.168.0.229"
sshpass -p "Bichito21$" ssh rodolfoarispe@192.168.0.229 "scutil --nc stop 'VPN'"
```

**Credenciales BD:**
- Servidor: `localhost:1414`
- Usuario: `analitica`
- Password: `biuser20!`

#### **🤖 PROTOCOLO PARA ASISTENTE:**
Cuando el usuario necesite acceso a producción:

1. **NUNCA ejecutar el script automáticamente**
2. **Recordar al usuario:** "Debes ejecutar manualmente: `./scripts/geca_prod.sh start`"
3. **El script pedirá la contraseña SSH interactivamente**
4. **Una vez conectado, puedes usar:** `-c proyectos_prod` para consultas
5. **Recordar al usuario desconectar:** `./scripts/geca_prod.sh stop`

#### **⚠️ REGLAS CRÍTICAS PARA PRODUCCIÓN:**
1. **NUNCA ejecutar sin confirmación explícita del usuario**
2. **SIEMPRE preguntar antes de cualquier operación**  
3. **SOLO consultas SELECT salvo indicación contraria**
4. **El script de conexión debe ejecutarse MANUALMENTE por el usuario**
5. **Recordar al usuario que debe ejecutar: `./scripts/geca_prod.sh start`**
6. **Limitar resultados** para evitar sobrecarga del servidor

#### **Tablas verificadas en Producción:**
- ✅ `temp_accounting_charges` / `temp_accounting_master` (Magaya)
- ✅ `temp_shipment_master` / `temp_shipment_charges` / `temp_shipment_items` (Magaya)
- ✅ `temp_sage_chart` / `temp_sage_*` (Sage/Peachtree) 
- ✅ Tablas adicionales: `temp_quotes_*`, `temp_payments_*`, `temp_cargo_release_*`

---

## ⚠️ LEER PRIMERO: Protocolo para Asistente IA

Antes de ejecutar cualquier comando, el asistente DEBE leer en este orden:

1. **CLAUDE.md** (2 min) - Índice maestro
2. **ASISTENTE_CHECKLIST.md** (3 min) - Checklist paso a paso  
3. **PROTOCOLO_CONSULTAS.yaml** (ref rápida) - Definición formal del protocolo
4. El documento especializado según la tarea (CONEXION_PRODUCCION.md, etc.)

Esto asegura que NO cometeré errores de orden de ejecución.

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

### Paso 3: Ejecutar SQL

Con la información de los pasos 1 y 2, construye y ejecuta la consulta SQL usando **los comandos disponibles**:

#### **Opción A: Comando SQL directo en main.py** ⭐
```bash
/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos_prod sql "SELECT * FROM temp_sage_chart LIMIT 10"
```

#### **Opción B: Script específico para producción** ⭐
```bash
/home/rodolfoarispe/vEnv/mem0/bin/python query_prod.py "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='VIEW'"
```

#### **Reglas importantes:**
- Usa los campos exactos del esquema (paso 2)
- Respeta las relaciones documentadas (paso 1)  
- Para rangos de fechas: cerrado-abierto (`>= inicio AND < fin`)
- Límite por defecto: 100 filas (usar `--limit N` para cambiar)

#### **Ejemplos prácticos:**
```bash
# Buscar vistas con 'sage' en el nombre
main.py -c proyectos_prod sql "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='VIEW' AND LOWER(TABLE_NAME) LIKE '%sage%'"

# Consulta con límite específico
query_prod.py "SELECT * FROM temp_shipment_master" --limit 50
```

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

### **Flujo de Trabajo Correcto:**
1. **Esquemas primero** → `main.py schema <tabla>` para obtener campos exactos
2. **Contexto después** → `main.py search "<pregunta>"` para entender relaciones  
3. **SQL al final** → `main.py -c proyectos_prod sql "<consulta>"` o `query_prod.py "<consulta>"`

### **Reglas Críticas:**
1. **Nunca asumas nombres de campos** → Siempre consulta el esquema primero
2. **Nunca uses tablas no documentadas** → Verifica que aparezcan en el esquema
3. **Para rangos de fechas** → Usa sintaxis cerrado-abierto: `>= '2025-01-01' AND < '2025-01-31'`
4. **Para servidor de producción** → NUNCA ejecutar sin confirmación explícita del usuario
5. **Comandos SQL disponibles:**
   - `main.py -c proyectos_prod sql "<query>"` 
   - `query_prod.py "<query>" --limit N`

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

---

## Archivos de Referencia del Sistema

### **GUIA.md** - Documentación Técnica Completa
- **Qué es:** Guía técnica del sistema de BD vectorial con ChromaDB y Ollama
- **Contenido:** Arquitectura, comandos, configuración, requisitos, troubleshooting
- **Cuándo consultar:** Para entender la arquitectura técnica, comandos específicos, o resolver problemas
- **Ubicación:** `/home/rodolfoarispe/bd_vectorial/GUIA.md`

### **collections.yaml** - Configuración Principal
- **Qué es:** Archivo de configuración que define colecciones, fuentes y conexiones
- **Contenido:** 
  - Configuración de Ollama (embedding + chat models)
  - Configuración de ChromaDB
  - Definición de colecciones (proyectos)
  - Fuentes de datos (documentacion + documentacion_prod)
  - Configuración sql_enrich para desarrollo y producción
- **Cuándo consultar:** Para verificar configuración actual o agregar nuevas fuentes
- **Ubicación:** `/home/rodolfoarispe/bd_vectorial/collections.yaml`

### **collections.secrets.yaml** - Credenciales Sensibles
- **Qué es:** Archivo con credenciales de bases de datos (no versionado)
- **Contenido:**
  - Credenciales desarrollo: `sa / nvoThund3r25!`
  - Credenciales producción: `analitica / biuser20!`
- **Ubicación:** `/home/rodolfoarispe/bd_vectorial/collections.secrets.yaml`
- **Seguridad:** Permisos restringidos (`chmod 600`)

### **Contexto Completo en Nueva Sesión**
Para obtener contexto completo del sistema en una nueva sesión, usar:
```
usa @AGENTS.md como contexto
```

Esto proporciona automáticamente acceso a:
- ✅ Flujo de trabajo híbrido (esquemas → contexto → SQL)
- ✅ Configuración de servidores GECA (desarrollo + producción)
- ✅ Reglas de seguridad y mejores prácticas
- ✅ Comandos y herramientas disponibles
- ✅ Referencias a GUIA.md y collections.yaml para detalles técnicos

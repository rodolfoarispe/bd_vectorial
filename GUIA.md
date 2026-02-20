# Base de Datos Vectorial - Guía Rápida

## ¿Qué es esto?

Un sistema que toma datos de archivos (CSV) y opcionalmente enriquece desde bases de datos (MSSQL, MariaDB, DuckDB), los convierte en vectores usando IA (Ollama) y los almacena en ChromaDB para hacer **búsquedas por significado**.

Ejemplo: buscas "embarques de china" y encuentra registros con puertos como Shanghai, Ningbo, Qingdao — sin que exista la palabra "china" en esos campos.

## Conceptos clave

- **Colección**: representa un contexto (ej: `proyectos`). Agrupa todo el conocimiento de ese contexto.
- **Source (fuente)**: un archivo o tabla dentro de una colección. Cada fuente define qué campos se vectorizan y cuáles son metadata.
- **Vectorizar**: convertir texto en números (768 dimensiones) que representan su significado. Textos similares = vectores cercanos.
- **Metadata**: campos que NO se vectorizan pero sirven para filtros exactos (ej: Status=Loaded).
- **`_source`**: metadata automática que indica de qué fuente vino cada registro (ej: `_source=shipments`).
- **Enrichment SQL**: añade esquemas (columnas/tipos) y catálogos (valores típicos) desde la BD usando las tablas declaradas en el CSV.

## Estructura del proyecto

```
collections.yaml   ← Configuración: colecciones, fuentes, conexiones, campos
collections.secrets.yaml ← Credenciales (no versionar)
config.py          ← Lee el YAML
db_connector.py    ← Conexiones a BD (MSSQL, MariaDB, DuckDB, CSV, JSON)
embeddings.py      ← Genera vectores con Ollama (nomic-embed-text)
vector_store.py    ← Almacena/consulta vectores en ChromaDB
search.py          ← Lógica de búsqueda semántica
main.py            ← CLI (interfaz de línea de comandos)
chroma_data/       ← Datos persistidos de ChromaDB (no tocar)
```

## Comandos

```bash
# Usar siempre con el venv:
PYTHON=/home/rodolfoarispe/vEnv/mem0/bin/python

# Verificar que todo esté conectado
$PYTHON main.py check

# Ver colecciones disponibles
$PYTHON main.py collections

# Indexar (convertir datos en vectores)
$PYTHON main.py -c proyectos index
$PYTHON main.py -c proyectos index --clear

# Buscar
$PYTHON main.py -c proyectos search "catalogos de Direction en embarques"
$PYTHON main.py -c proyectos search "esquema de temp_shipment_master"

# Modo interactivo
$PYTHON main.py -c proyectos interactive

# Estadísticas
$PYTHON main.py -c proyectos stats
```

## Cómo agregar conocimiento nuevo

### Agregar reglas de negocio (CSV)

Editar `data/proyectos_documentacion.csv` y añadir filas con esta estructura:

```csv
id,cliente,proyecto,modulo,entidad,tabla,pk,fk,dimensiones,campos_clave,descripcion,logica_negocio,sql,supuestos,notas,owner,estado,version,fecha,tags
```

Campos recomendados:
- `tabla`, `pk`, `fk`: para relaciones
- `dimensiones`: columnas tipo catálogo (se enriquecen con SQL)
- `campos_clave`: columnas importantes para el negocio

Luego reindexar:
```bash
$PYTHON main.py -c proyectos index --clear
```

### Enrichment SQL (catálogos + esquema)

En `collections.yaml`, dentro de la fuente `documentacion`, usa `sql_enrich` para conectar al DWH:

```yaml
sql_enrich:
  type: mssql
  server: "192.168.0.14"
  port: 1433
  database: "analitica"
  auth: credentials
  user: "REPLACE_IN_SECRETS"
  password: "REPLACE_IN_SECRETS"
  max_values: 50
  include_schema: true
  max_columns: 200
```

Credenciales en `collections.secrets.yaml`.

## Tipos de conexión soportados

| type | auth | Campos requeridos |
|------|------|-------------------|
| mssql | credentials | server, port, database, user, password |
| mssql | trusted | server, port, database |
| mariadb | credentials | server, port, database, user, password |
| duckdb | — | path |
| csv | — | path |
| json | — | path |

## Qué campos vectorizar vs metadata

**Vectorizar** (búsqueda semántica): campos con texto descriptivo — nombres, descripciones, notas, direcciones. Son los campos donde quieres buscar "por significado".

**Metadata** (filtros exactos): campos con valores discretos — status, categorías, países, fechas, montos. Son los campos donde filtras con `campo=valor`.

**Regla práctica**: si el campo tiene texto libre → vectorizar. Si tiene valores fijos/numéricos → metadata. Un campo puede estar en ambos si tiene sentido.

## Requisitos

- **Ollama** corriendo (`ollama serve`) con modelo `nomic-embed-text`
- **Python 3.12** con venv en `/home/rodolfoarispe/vEnv/mem0/`
- Paquetes: pymssql, pymysql, duckdb, chromadb, pandas, pyyaml, requests

## Mover el proyecto a otra ubicación

Si necesitas trasladar todo el proyecto a otra máquina o ubicación:

### Archivos y carpetas críticos a mover

```
bd_vectorial/
├── data/
│   ├── proyectos_documentacion.csv    ← FUENTE DE VERDAD
│   └── schemas_cache.json              ← Caché de esquemas
├── chroma_data/                        ← Base de datos vectorial
├── collections.yaml                    ← Configuración de colecciones
├── collections.secrets.yaml            ← ⚠️ CREDENCIALES SENSIBLES
├── AGENTS.md                           ← Instrucciones del sistema
├── GUIA.md                             ← Esta guía
├── *.py                                ← Código fuente
├── requirements.txt                    ← Dependencias
└── vEnv/mem0/                          ← Entorno Python virtual (opcional)
```

### Comando para copiar

**En la misma máquina:**
```bash
cp -r /home/rodolfoarispe/bd_vectorial /nueva/ruta/bd_vectorial
```

**A otra máquina:**
```bash
scp -r /home/rodolfoarispe/bd_vectorial usuario@host:/nueva/ruta/
```

### Después de mover

1. **Verificar credenciales en `collections.secrets.yaml`**
   ```bash
   cd /nueva/ruta/bd_vectorial
   cat collections.secrets.yaml
   ```
   Las credenciales deben coincidir con la BD de la nueva ubicación.

2. **Recrear el entorno virtual (si es necesario)**
   ```bash
   cd /nueva/ruta/bd_vectorial
   python3 -m venv vEnv/mem0
   source vEnv/mem0/bin/activate
   pip install -r requirements.txt
   ```

3. **Verificar conexión**
   ```bash
   /nueva/ruta/bd_vectorial/vEnv/mem0/bin/python main.py check
   ```

4. **Reindexear (opcional pero recomendado)**
   ```bash
   /nueva/ruta/bd_vectorial/vEnv/mem0/bin/python main.py -c proyectos index --clear
   ```

### Archivos que NO necesitan moverse

- `__pycache__/` - Se regenera automáticamente
- `.claude/` - Configuración local del IDE
- `.mcp.json` - Configuración local

### ⚠️ IMPORTANTE

Sin estos archivos, el sistema **NO funciona**:
- `collections.yaml` - Configuración de colecciones
- `collections.secrets.yaml` - Credenciales de BD
- `data/proyectos_documentacion.csv` - Documentación fuente
- `chroma_data/` - Embeddings vectoriales (o regenerar con `index --clear`)

---

## Notas importantes

- **Re-indexar**: si cambian los datos en la BD fuente, hay que re-indexar para que los cambios se reflejen. ChromaDB no se sincroniza automáticamente.
- **Similitud**: las búsquedas siempre devuelven resultados, aunque no sean relevantes. Similitudes por debajo de ~0.5 generalmente no son útiles.
- **Límites**: para pruebas usa `--limit`. Para producción indexa todo sin límite.
- **`--clear`**: borra TODA la colección antes de indexar.
- **Credenciales**: usar `collections.secrets.yaml` con permisos restringidos (`chmod 600`).

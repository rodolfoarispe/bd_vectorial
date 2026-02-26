# Análisis: Orden de Ejecución del Asistente IA

## El Problema

Cuando me pidieron "quiero ver las vistas de producción de GECA que tienen la palabra sage en el nombre", cometí estos errores:

1. ❌ **No revisar documentación disponible primero**
   - Intenté conexiones directas sin leer CLAUDE.md, CONEXION_PRODUCCION.md
   - Asumí cómo ejecutar comandos sin verificar

2. ❌ **Orden de búsqueda de información caótico**
   - Probé main.py sin verificar si tenía comando 'sql'
   - Intenté conexiones sin validar que el túnel estaba activo
   - Usé db_connector.py directamente sin verificar la interfaz pública

3. ❌ **Falta de "protocolo de descubrimiento"**
   - No hay un flujo sistemático para identificar qué necesito
   - Cada comando lo intenté "a ciegas" con múltiples errores
   - Desperdicié tokens y tiempo intentando cosas que ya estaban documentadas

## Flujo ACTUAL (Erróneo)

```
Usuario pide algo
    ↓
Intento solución directa (falla)
    ↓
Busco en código (falla)
    ↓
Intento alternativa (falla)
    ↓
Pido que lea documentación...
```

**Resultado:** Muchos intentos fallidos, confusión, frustración del usuario.

---

## Flujo PROPUESTO (Correcto)

### Fase 1: DESCUBRIMIENTO (Lectura de documentación)

**PRIMERO: Leer el Índice Maestro**
```
CLAUDE.md
  ├─ Propósito del proyecto
  ├─ Archivos y CUÁNDO usarlos (MAP de decisiones)
  └─ Reglas críticas
```

**BASADO EN LA PREGUNTA DEL USUARIO:**

```
¿Es pregunta sobre conexión?
├─ SÍ → CONEXION_PRODUCCION.md
└─ NO → ¿Es pregunta sobre BD de desarrollo?
        ├─ SÍ → Usar proyectos (no prod)
        └─ NO → ¿Necesita contexto de negocio?
                ├─ SÍ → AGENTS.md (flujo híbrido)
                └─ NO → GUIA.md (arquitectura técnica)
```

**SEGUNDA: Verificar disponibilidad de documentación específica**
```
¿Qué tabla/tema necesito?
├─ Magaya (shipments, charges) → data/proyectos_documentacion.csv
├─ Sage/Peachtree → data/sage_schema_notes.md
└─ Facturas/Jobs → data/sage_facturas_jobs_analisis.md
```

### Fase 2: VALIDACIÓN (Verificar prerequisitos)

Antes de intentar cualquier comando, validar:

```python
class MisiónAsistente:
    def validar_prerequisitos(self, tarea):
        checks = {
            "¿Qué documentación necesito?": self.mapear_documentacion(),
            "¿Qué ambiente?": self.verificar_ambiente(),
            "¿Credenciales/conexión?": self.verificar_conexion(),
            "¿Comandos correctos?": self.verificar_api(),
        }
        return all(checks.values())
```

**EJEMPLO: Para "vistas con sage en producción"**

| Pregunta | Respuesta | Fuente |
|----------|----------|--------|
| ¿Desarrollo o Producción? | Producción | Usuario pidió "producción" |
| ¿Script de conexión? | ./scripts/geca_prod.sh | CONEXION_PRODUCCION.md:20 |
| ¿Túnel activo? | Verificar con status | CONEXION_PRODUCCION.md:59 |
| ¿Comando SQL disponible? | main.py sql o query_prod.py | AGENTS.md:183 |
| ¿Tabla/Vista disponible? | Validar en INFORMATION_SCHEMA | CONEXION_PRODUCCION.md:72 |

### Fase 3: EJECUCIÓN (En orden)

```bash
# 1. Verificar documentación relevante
cat CLAUDE.md                           # Índice maestro
grep -l "producción" CONEXION_PRODUCCION.md  # Contextualizar

# 2. Validar prerequisitos
./scripts/geca_prod.sh status           # ¿Túnel está activo?

# 3. Ejecutar (ahora con info completa)
main.py -c proyectos_prod sql "SELECT ..."
```

---

## Propuesta de Mejora: "Protocolo de Descubrimiento"

### Sistema de Preguntas Automáticas

Cuando reciba una tarea, hacer estas preguntas ANTES de intentar:

```python
PROTOCOLO_DESCUBRIMIENTO = {
    "¿Qué tipo de tarea es?": [
        "Consulta a BD",
        "Búsqueda semántica",
        "Análisis de código",
        "Configuración del sistema"
    ],
    
    "¿Ambiente?": [
        "Desarrollo (192.168.0.14:1433)",
        "Producción (192.168.1.11:1414)"
    ],
    
    "¿Sistema?": [
        "Magaya (embarques, cargos)",
        "Sage/Peachtree (contabilidad)",
        "Híbrido (ambos)"
    ],
    
    "¿Qué documentación necesito?": [
        "CLAUDE.md - Índice maestro",
        "AGENTS.md - Flujo de trabajo",
        "CONEXION_PRODUCCION.md - Producción",
        "data/proyectos_documentacion.csv - Magaya",
        "data/sage_schema_notes.md - Sage"
    ]
}
```

### Implementación: Herramienta "Protocolo" 

Crear un archivo que me guíe automáticamente:

```yaml
# PROTOCOLO_CONSULTAS.yaml
protocolos:
  consulta_bd:
    paso_1_lectura:
      - archivo: CLAUDE.md
        seccion: "Archivos de documentación y cuándo usarlos"
        razon: "Índice maestro de dónde buscar"
      
      - archivo: CONEXION_PRODUCCION.md (si es producción)
        seccion: "Proceso de Conexión"
        razon: "Verificar cómo conectar"
    
    paso_2_validacion:
      - verificar: "¿Qué tabla necesito?"
        accion: "main.py schema <tabla>"
      
      - verificar: "¿Contexto de negocio?"
        accion: "main.py search <tema>"
      
      - verificar: "¿Producción conectada?"
        accion: "./scripts/geca_prod.sh status"
    
    paso_3_ejecucion:
      - comando: "main.py -c [proyectos|proyectos_prod] sql"
        razon: "Ejecutar SQL con información verificada"
```

---

## Checklist: Qué Debería Haber Hecho

✅ **Paso 1: Lectura de documentación (5 minutos)**
- [ ] Leer CLAUDE.md completo
- [ ] Identificar que pregunta es sobre Producción + Sage
- [ ] Revisar CONEXION_PRODUCCION.md
- [ ] Revisar AGENTS.md sección "Paso 3: Ejecutar SQL"

✅ **Paso 2: Validación de prerequisitos (2 minutos)**
- [ ] ¿Túnel SSH activo? → ./scripts/geca_prod.sh status
- [ ] ¿Comando SQL disponible? → Verificar en main.py help
- [ ] ¿Credenciales correctas? → collections.secrets.yaml

✅ **Paso 3: Ejecución (1 minuto)**
- [ ] main.py -c proyectos_prod sql "SELECT ..."

**Total: 8 minutos sin errores**

**Lo que hice: 30+ minutos con 10+ intentos fallidos**

---

## Cómo Implementar la Mejora

### Opción 1: Adicionar archivo de protocolo

Crear `PROTOCOLO_CONSULTAS.yaml` con flowchart de decisiones.
- Ventaja: Máquina legible, se puede usar programáticamente
- Desventaja: Requiere que lo interprete correctamente

### Opción 2: Actualizar CLAUDE.md

Agregar sección "COMO DEBERÍA PROCEDER EL ASISTENTE" con checklist.
- Ventaja: Información centralizada
- Desventaja: Depende de que lo lea

### Opción 3: Sistema de reglas explicitas (RECOMENDADO)

Crear archivo de instrucciones explícitas que mencionen:

```markdown
## ORDEN DE ACCIONES DEL ASISTENTE

1. **SIEMPRE leer primero:**
   - Leer CLAUDE.md líneas 1-20 (propósito y archivos)
   - Basado en la pregunta, identificar qué archivo especializado leer
   - NUNCA saltarse este paso

2. **SIEMPRE validar ANTES de ejecutar:**
   - Si es producción: ./scripts/geca_prod.sh status
   - Si es SQL: verificar tabla con main.py schema
   - Si necesita contexto: main.py search

3. **SOLO ENTONCES ejecutar comandos**
```

---

## Recomendación Final

**Implementar todas las opciones:**

1. ✅ **Actualizar CLAUDE.md** con sección "PROTOCOLO PARA EL ASISTENTE"
2. ✅ **Crear PROTOCOLO_CONSULTAS.yaml** como referencia rápida
3. ✅ **Agregar al top del código** comentario: "LEE CLAUDE.md PRIMERO"
4. ✅ **Crear checklist** en nuevo archivo: ASISTENTE_CHECKLIST.md

Esto asegura que:
- No depende solo de mi "memoria"
- Es explícito y verificable
- Cualquier IA que lea el proyecto sabrá el protocolo correcto
- El usuario puede auditar si estoy siguiendo el protocolo


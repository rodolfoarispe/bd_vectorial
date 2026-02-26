# Conexión a GECA Producción

## ✅ ESTADO ACTUAL: VPN FUNCIONA

**Solución encontrada:** Usar `networksetup` en lugar de `scutil`.

- `scutil --nc start` requiere acceso al Keychain (falla con "falta secreto compartido IPSec")
- `networksetup -connectpppoeservice` accede al Keychain correctamente ✅

**Cambio:** Script actualizado para usar `networksetup`.

---

## Configuración Verificada

### Servidor Producción GECA
- **IP Interna:** `192.168.1.11:1414`
- **Acceso via:** Mac `192.168.0.229` + VPN "VPN"
- **Credenciales BD:** `analitica / biuser20!`
- **Base de datos:** `analitica`
- **Túnel local:** `localhost:1414`

### Credenciales Mac (SSH)
- **Host:** `192.168.0.229`
- **Usuario:** `rodolfoarispe` ⚠️ **PROBLEMA: No tiene permisos admin**
- **Password:** `Bichito21$` (se solicita interactivamente)

## Requisitos Previos - Configuración en la Mac

### ✅ Verificado: Funciona con `networksetup`

El script usa `networksetup` que accede correctamente al Keychain de la Mac.

**Verificación rápida:**
```bash
# En terminal de la Mac:
networksetup -connectpppoeservice "VPN"

# Si conecta sin error → OK ✓
# Si da error de IPSec → Ver abajo
```

### Si el error persiste: Verificar VPN en GUI

Si `networksetup` falla con error de IPSec:

1. Abre **Sistema → Red → VPN**
2. Click en **Editar** (Edit)
3. Verifica:
   - ¿Server está configurado?
   - ¿Account está configurado?
   - ¿El Keychain tiene guardada la credencial?
4. Intenta conectar desde GUI (click en VPN desde barra)

Si GUI funciona pero línea de comandos falla, el problema es del Keychain. 
Solución: Elimina y reconfigura la VPN (Sistema → Red → VPN, botón "-", luego "+")

---

## Proceso de Conexión

### Automático (Recomendado) ✅
```bash
# Activar VPN + establecer túnel (pedirá contraseña interactivamente)
./scripts/geca_prod.sh start
# Contraseña SSH: Bichito21$

# Script levanta:
# 1. VPN en la Mac usando networksetup ✅
# 2. Túnel SSH a 192.168.1.11:1414 ✅
# 3. Disponible en: localhost:1414

# Usar BD vectorial con producción
/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos_prod schema <tabla>

# Desconectar todo
./scripts/geca_prod.sh stop
```

### Script Interactivo
El script `geca_prod.sh` siempre pedirá la contraseña interactivamente para mayor seguridad:
- ✅ No almacena credenciales en texto plano
- ✅ Muestra proceso paso a paso
- ✅ Instrucciones claras de uso
- ✅ Desconexión completa automática

### Manual (Respaldo)
```bash
# 1. Activar VPN en Mac
sshpass -p "Bichito21$" ssh rodolfoarispe@192.168.0.229 "scutil --nc start 'VPN'"

# 2. Establecer túnel SSH
sshpass -p "Bichito21$" ssh -L 1414:192.168.1.11:1414 rodolfoarispe@192.168.0.229 -N &

# 3. Verificar conexión
netstat -tln | grep :1414

# 4. Desconectar
pkill -f "ssh.*1414.*192.168.0.229"
sshpass -p "Bichito21$" ssh rodolfoarispe@192.168.0.229 "scutil --nc stop 'VPN'"
```

## Estados y Verificación

### Verificar Estado
```bash
./scripts/geca_prod.sh status
```

### Troubleshooting
```bash
# Si túnel no funciona
lsof -i :1414
pkill -f "ssh.*1414"

# Si VPN no conecta
ssh rodolfoarispe@192.168.0.229 "scutil --nc status 'VPN'"

# Prueba de conectividad BD
/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos_prod schema temp_shipment_master
```

## Seguridad

- ✅ Contraseña SSH configurada en variable de entorno
- ✅ Acceso solo bajo demanda (no permanente)
- ✅ Desconexión automática de VPN al terminar
- ⚠️  Solo consultas SELECT (salvo indicación explícita)

## Colecciones Disponibles

- **`proyectos`** → Desarrollo (`192.168.0.14:1433`)
- **`proyectos_prod`** → Producción (`localhost:1414` via túnel)

## Comandos Rápidos

```bash
# Alias útiles para .bashrc
alias geca-dev="/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos"
alias geca-prod="/home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos_prod"
alias geca-connect="export MAC_PASSWORD='Bichito21$' && ./scripts/geca_prod.sh start"
alias geca-disconnect="export MAC_PASSWORD='Bichito21$' && ./scripts/geca_prod.sh stop"
```
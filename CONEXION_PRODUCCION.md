# Conexión a GECA Producción

## ⚠️ ESTADO ACTUAL: VPN NO FUNCIONA

**Problema identificado:** El script no puede levantar la VPN en la Mac.

**Causa probable:** El usuario `rodolfoarispe` NO tiene permisos de administrador para ejecutar `scutil --nc start` en la Mac.

**Requerimiento:** Necesitas un usuario CON permisos de administrador en la Mac `192.168.0.229` para poder levantar la VPN.

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

### Problema: Usuario sin permisos de administrador

Para que el script pueda activar la VPN, el usuario en la Mac DEBE tener permisos de administrador.

**¿Cómo verificar en la Mac?**

```bash
# Ejecutar en terminal de la Mac:
sudo scutil --nc list

# Si pide contraseña y la acepta → TIENE permisos ✓
# Si dice "Operation not permitted" → NO TIENE permisos ✗
```

**¿Cómo arreglarlo en la Mac?**

```bash
# Opción 1: Agregar usuario a grupo admin
sudo dseditgroup -o edit -a rodolfoarispe -t user admin

# Opción 2: Permitir sudoers sin contraseña (menos seguro)
sudo visudo
# Agregar línea: rodolfoarispe ALL=(ALL) NOPASSWD: /usr/bin/scutil
```

**Alternativa: Ejecutar manualmente en la Mac**

Si no puedes cambiar permisos, usa este script directamente en la Mac:

```bash
# En la Mac (192.168.0.229):
sudo scutil --nc start "VPN"
sudo scutil --nc status "VPN"

# Verificar
sudo scutil --nc list  # Debe mostrar "VPN" en estado "Connected"
```

---

## Proceso de Conexión

### Automático (Recomendado) - REQUIERE permisos en la Mac
```bash
# Activar VPN + establecer túnel (pedirá contraseña interactivamente)
./scripts/geca_prod.sh start
# Contraseña SSH: Bichito21$

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
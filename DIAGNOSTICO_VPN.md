# Diagnóstico: Por qué la VPN no se levanta

## ✅ SOLUCIÓN ENCONTRADA

**Problema:** `scutil --nc start` fallaba con "falta secreto compartido IPSec"

**Solución:** Usar `networksetup -connectpppoeservice "VPN"` en lugar de `scutil`

**Razón:** `scutil` necesita acceso al Keychain que no estaba disponible. `networksetup` accede correctamente al Keychain.

**Script actualizado:** Ya incluye la solución.

---

## Causas Posibles (Histórico)

### Causa 1: Usuario sin permisos de administrador (DESCARTADA)

**Síntoma:** El comando `scutil --nc start` falla silenciosamente sin error

**Diagnóstico:**
```bash
# Ejecuta DESDE ESTA MÁQUINA:
ssh rodolfoarispe@192.168.0.229 "sudo scutil --nc list"

# Si pide contraseña en el prompt → NO tiene permisos sin contraseña
# Si falla con "Operation not permitted" → NO tiene permisos absolutos
```

**Solución en la Mac (requiere admin):**
```bash
# Opción A: Agregar usuario al grupo admin
sudo dseditgroup -o edit -a rodolfoarispe -t user admin

# Opción B: Permitir scutil sin contraseña (menos seguro)
sudo visudo
# Agregar esta línea:
rodolfoarispe ALL=(ALL) NOPASSWD: /usr/bin/scutil
```

---

### Causa 2: VPN no configurada correctamente

**Síntoma:** La VPN existe pero dice "Error - falta secreto compartido IPSec"

**Diagnóstico:**
```bash
# En la Mac:
scutil --nc list
scutil --nc status "VPN"
```

**Solución:** Reconfigura la VPN en la Mac (Sistema → Red → VPN)

---

### Causa 3: El nombre de la VPN es incorrecto

**Síntoma:** "No se encuentra conexión con ese nombre"

**Diagnóstico:**
```bash
# En la Mac, listar todas las VPNs disponibles:
scutil --nc list
```

**Solución:** Actualiza `VPN_NAME="..."` en `geca_prod.sh`

---

## Script de Diagnóstico Automático

Copia esto en una terminal para diagnosticar automáticamente:

```bash
#!/bin/bash

MAC_HOST="192.168.0.229"
MAC_USER="rodolfoarispe"
VPN_NAME="VPN"

echo "🔍 DIAGNÓSTICO VPN EN MAC"
echo "=========================="
echo ""

# Test 1: ¿Puedo conectar por SSH?
echo "1️⃣  Verificando conectividad SSH..."
if ssh -o ConnectTimeout=5 $MAC_USER@$MAC_HOST "echo OK" >/dev/null 2>&1; then
    echo "   ✅ SSH conecta correctamente"
else
    echo "   ❌ No puedo conectar por SSH"
    exit 1
fi

# Test 2: ¿Tiene permisos para scutil?
echo ""
echo "2️⃣  Verificando permisos de administrador..."
SUDO_TEST=$(ssh $MAC_USER@$MAC_HOST "sudo scutil --nc list 2>&1" | grep -i "operation not permitted" || echo "OK")
if [[ "$SUDO_TEST" == "OK" ]]; then
    echo "   ✅ Usuario TIENE permisos sudo para scutil"
else
    echo "   ❌ Usuario NO TIENE permisos sudo para scutil"
    echo "   Solución: Ver DIAGNOSTICO_VPN.md Causa 1"
fi

# Test 3: ¿Existe la VPN?
echo ""
echo "3️⃣  Buscando VPN '$VPN_NAME'..."
VPN_EXISTS=$(ssh $MAC_USER@$MAC_HOST "scutil --nc list 2>&1 | grep -i '$VPN_NAME'" | wc -l)
if [ $VPN_EXISTS -gt 0 ]; then
    echo "   ✅ VPN '$VPN_NAME' existe en la Mac"
else
    echo "   ❌ VPN '$VPN_NAME' NO existe"
    echo "   VPNs disponibles:"
    ssh $MAC_USER@$MAC_HOST "scutil --nc list"
    exit 1
fi

# Test 4: ¿Cuál es su estado actual?
echo ""
echo "4️⃣  Estado actual de la VPN..."
VPN_STATUS=$(ssh $MAC_USER@$MAC_HOST "scutil --nc status '$VPN_NAME' 2>&1 | head -1")
echo "   Estado: $VPN_STATUS"

if [[ "$VPN_STATUS" == *"Connected"* ]]; then
    echo "   ✅ VPN ESTÁ CONECTADA"
elif [[ "$VPN_STATUS" == *"Disconnected"* ]]; then
    echo "   ℹ️  VPN está desconectada (normal si no se ha conectado)"
elif [[ "$VPN_STATUS" == *"IPSec"* ]] || [[ "$VPN_STATUS" == *"shared secret"* ]]; then
    echo "   ❌ ERROR EN VPN: Falta secreto compartido IPSec"
    echo "   Solución: Reconfigura VPN en Mac (Sistema → Red → VPN)"
else
    echo "   ⚠️  Estado desconocido: $VPN_STATUS"
fi

echo ""
echo "=========================="
echo "✅ Diagnóstico completado"
```

---

## Recomendaciones

### A Corto Plazo (Temporal)

Si no tienes acceso a cambiar permisos en la Mac, ejecuta manualmente en la Mac:

```bash
# En la Mac (abre terminal)
sudo scutil --nc start "VPN"

# Luego desde tu máquina:
ssh -L 1414:192.168.1.11:1414 rodolfoarispe@192.168.0.229 -N &

# Verifica:
nc -zv localhost 1414
```

---

### A Largo Plazo (Permanente)

Necesitas que alguien con acceso de administrador a la Mac ejecute:

```bash
# En la Mac:
sudo dseditgroup -o edit -a rodolfoarispe -t user admin
```

O configura sudoers:

```bash
# En la Mac:
sudo visudo
# Agregar:
rodolfoarispe ALL=(ALL) NOPASSWD: /usr/bin/scutil
```

---

## Próximos Pasos

1. **Ejecuta el script de diagnóstico** para identificar la causa exacta
2. **Aplica la solución** según la causa
3. **Prueba:** `./scripts/geca_prod.sh start`


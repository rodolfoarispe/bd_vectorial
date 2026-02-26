#!/bin/bash
# Script para conectar a GECA Producción bajo demanda
# 
# DESCRIPCIÓN:
# Este script automatiza la conexión al servidor GECA de producción que requiere:
# 1. Activar VPN "VPN" en el Mac 192.168.0.229
# 2. Establecer túnel SSH hacia 192.168.1.11:1414
# 3. Hacer disponible la BD en localhost:1414
#
# USAGE: ./geca_prod.sh [start|stop|status|force-stop|test|help]

TUNNEL_PORT=1414
MAC_HOST="192.168.0.229"
VPN_NAME="VPN"

# Mostrar encabezado informativo
show_header() {
    echo "🏢 GECA Producción - Control de Conexión"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📍 Servidor: 192.168.1.11:1414 (via túnel SSH)"
    echo "🖥️  Mac Gateway: $MAC_HOST"
    echo "🔗 VPN requerida: '$VPN_NAME'"
    echo "🏠 Disponible en: localhost:$TUNNEL_PORT"
    echo ""
}

# Solicitar contraseña del Mac (siempre interactiva)
request_password() {
    echo "🔐 Credenciales requeridas:"
    echo -n "   Contraseña SSH para rodolfoarispe@$MAC_HOST: "
    read -s MAC_PASSWORD
    echo ""
    echo ""
}

# Función helper para SSH con contraseña
ssh_mac() {
    sshpass -p "$MAC_PASSWORD" ssh -o StrictHostKeyChecking=no rodolfoarispe@$MAC_HOST "$@"
}

# Función helper para SSH túnel con contraseña
ssh_tunnel() {
    sshpass -p "$MAC_PASSWORD" ssh -o StrictHostKeyChecking=no -L $TUNNEL_PORT:192.168.1.11:1414 rodolfoarispe@$MAC_HOST -N &
}

case "${1:-help}" in
    "start")
        show_header
        request_password
        
        echo "🔄 INICIANDO CONEXIÓN A PRODUCCIÓN..."
        echo ""
        
        echo "   1️⃣  Activando VPN '$VPN_NAME' en Mac $MAC_HOST..."
        ssh_mac "scutil --nc start '$VPN_NAME'"
        
        if [ $? -eq 0 ]; then
            echo "   ⏳ Esperando estabilización de conexión VPN (10s)..."
            sleep 10
            
            # VALIDACIÓN CRÍTICA: Verificar que VPN está REALMENTE conectada
            echo "   🔍 Verificando estado REAL de VPN..."
            VPN_FINAL_STATUS=$(ssh_mac "scutil --nc status '$VPN_NAME'" | head -1)
            if [[ "$VPN_FINAL_STATUS" == *"Connected"* ]]; then
                echo "   ✅ VPN activada y conectada correctamente: $VPN_FINAL_STATUS"
            else
                echo "   ❌ ERROR: VPN no está realmente conectada"
                echo "   📋 Estado: $VPN_FINAL_STATUS"
                echo ""
                echo "   Causas comunes:"
                echo "   • Falta secreto compartido IPSec"
                echo "   • Configuración VPN inválida en la Mac"
                echo "   • Problemas de red en la Mac"
                echo ""
                echo "   Acción: Revisa la configuración VPN en la Mac (Sistema → Red → VPN)"
                exit 1
            fi
            
            # Verificar si el túnel ya existe
            if lsof -i :$TUNNEL_PORT >/dev/null 2>&1; then
                echo "   ⚠️  Puerto $TUNNEL_PORT ya está en uso. Cerrando túnel existente..."
                pkill -f "ssh.*$TUNNEL_PORT.*$MAC_HOST"
                sleep 2
            fi
            
            echo "   2️⃣  Estableciendo túnel SSH hacia 192.168.1.11:1414..."
            ssh_tunnel
            
            sleep 3
            if lsof -i :$TUNNEL_PORT >/dev/null 2>&1; then
                echo "   ✅ Túnel SSH establecido en puerto $TUNNEL_PORT"
                
                # VALIDACIÓN CRÍTICA: Verificar que el servidor está realmente alcanzable
                echo "   🔍 Verificando conectividad a BD..."
                sleep 2
                if timeout 5 nc -zv localhost $TUNNEL_PORT >/dev/null 2>&1; then
                    echo "   ✅ Servidor GECA es alcanzable en localhost:$TUNNEL_PORT"
                    echo ""
                    echo "🎉 ¡CONEXIÓN ESTABLECIDA CORRECTAMENTE!"
                    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    echo "🌐 GECA Producción disponible en: localhost:$TUNNEL_PORT"
                    echo "👤 Usuario BD: analitica"
                    echo "🔑 Password BD: biuser20!"
                    echo "💾 Base de datos: analitica"
                    echo ""
                    echo "📝 Para desconectar ejecutar: $0 stop"
                else
                    echo "   ⚠️  ADVERTENCIA: Túnel SSH existe pero BD no responde"
                    echo "   Causas posibles:"
                    echo "   • VPN en la Mac no está realmente conectada"
                    echo "   • Falta secreto compartido IPSec"
                    echo "   • Servidor GECA no está disponible"
                    echo ""
                    echo "   Verifica: $0 status"
                    exit 1
                fi
            else
                echo "   ❌ Error al establecer túnel SSH"
                echo "   Verifica credenciales SSH en la Mac"
                exit 1
            fi
        else
            echo "❌ Error al activar VPN"
            exit 1
        fi
        ;;
        
    "stop")
        show_header
        request_password
        
        echo "🔄 DESCONECTANDO DE PRODUCCIÓN..."
        echo ""
        
        echo "   1️⃣  Cerrando túnel SSH..."
        if lsof -i :$TUNNEL_PORT >/dev/null 2>&1; then
            pkill -f "ssh.*$TUNNEL_PORT.*$MAC_HOST"
            sleep 2
            if lsof -i :$TUNNEL_PORT >/dev/null 2>&1; then
                echo "   ⚠️  Forzando cierre de túnel..."
                pkill -9 -f "ssh.*$TUNNEL_PORT.*$MAC_HOST"
                sleep 1
            fi
            echo "   ✅ Túnel SSH cerrado"
        else
            echo "   ℹ️  Túnel SSH ya estaba cerrado"
        fi
        
        echo "   2️⃣  Desactivando VPN '$VPN_NAME' en Mac..."
        VPN_CURRENT_STATUS=$(ssh_mac "scutil --nc status '$VPN_NAME'" | head -1)
        if [[ "$VPN_CURRENT_STATUS" == *"Connected"* ]]; then
            ssh_mac "scutil --nc stop '$VPN_NAME'"
            sleep 3
            VPN_NEW_STATUS=$(ssh_mac "scutil --nc status '$VPN_NAME'" | head -1)
            if [[ "$VPN_NEW_STATUS" == *"Disconnected"* ]]; then
                echo "   ✅ VPN desconectada correctamente"
            else
                echo "   ⚠️  VPN podría seguir conectada: $VPN_NEW_STATUS"
            fi
        else
            echo "   ℹ️  VPN ya estaba desconectada: $VPN_CURRENT_STATUS"
        fi
        
        echo ""
        echo "🔒 DESCONEXIÓN COMPLETA"
        echo "━━━━━━━━━━━━━━━━━━━━━━━"
        ;;
        
    "status")
        show_header
        request_password
        
        echo "📊 ESTADO ACTUAL DE CONEXIÓN"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        # Estado VPN
        echo "1️⃣  VPN Status en Mac ($MAC_HOST):"
        VPN_STATUS=$(ssh_mac "scutil --nc status '$VPN_NAME'" 2>&1 | head -1)
        if [[ "$VPN_STATUS" == *"Connected"* ]]; then
            echo "    ✅ Conectada: $VPN_STATUS"
        else
            echo "    ❌ NO conectada: $VPN_STATUS"
        fi
        echo ""
        
        # Estado túnel
        echo "2️⃣  Túnel SSH:"
        if lsof -i :$TUNNEL_PORT >/dev/null 2>&1; then
            echo "    ✅ Proceso SSH activo en puerto $TUNNEL_PORT"
            
            # Verificación adicional: ¿Realmente sirve?
            if timeout 3 nc -zv localhost $TUNNEL_PORT >/dev/null 2>&1; then
                echo "    ✅ Servidor GECA es alcanzable"
            else
                echo "    ❌ Puerto abierto pero servidor NO responde"
            fi
        else
            echo "    ❌ Inactivo"
        fi
        echo ""
        
        # Resumen
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        if [[ "$VPN_STATUS" == *"Connected"* ]] && lsof -i :$TUNNEL_PORT >/dev/null 2>&1; then
            echo "✅ CONEXIÓN OPERATIVA"
        else
            echo "❌ CONEXIÓN INCOMPLETA O FALLIDA"
            echo "   Ejecuta: $0 start (para reconectar)"
        fi
        ;;
        
    "force-stop")
        echo "🛑 Forzando cierre completo..."
        pkill -9 -f "ssh.*$TUNNEL_PORT.*$MAC_HOST" 2>/dev/null
        ssh_mac "scutil --nc stop '$VPN_NAME'" 2>/dev/null
        echo "✅ Forzado completamente"
        ;;
        
    "test")
        echo "🧪 Probando conectividad a BD de producción..."
        if lsof -i :$TUNNEL_PORT >/dev/null 2>&1; then
            cd /home/rodolfoarispe/bd_vectorial
            /home/rodolfoarispe/vEnv/mem0/bin/python main.py -c proyectos_prod schema temp_shipment_master | head -5
            if [ $? -eq 0 ]; then
                echo "✅ Conexión a BD funcionando correctamente"
            else
                echo "❌ Error al conectar con BD"
            fi
        else
            echo "❌ Túnel SSH no está activo"
        fi
        ;;
        
    "help"|*)
        show_header
        echo "📋 COMANDOS DISPONIBLES:"
        echo ""
        echo "   $0 start      - 🟢 Conectar a producción (VPN + túnel SSH)"
        echo "   $0 stop       - 🔴 Desconectar completamente (VPN + túnel)"
        echo "   $0 status     - 📊 Mostrar estado actual de conexiones"
        echo "   $0 test       - 🧪 Probar conectividad a base de datos"
        echo "   $0 force-stop - ⚠️  Forzar cierre completo (emergencias)"
        echo "   $0 help       - 📖 Mostrar esta ayuda"
        echo ""
        echo "🔄 FLUJO TÍPICO DE TRABAJO:"
        echo "   1. $0 start          # Conectar (pedirá contraseña)"
        echo "   2. Trabajar con BD   # Usar localhost:1414"  
        echo "   3. $0 stop           # Desconectar al terminar"
        echo ""
        echo "📡 CONEXIÓN DESTINO:"
        echo "   • Servidor interno: 192.168.1.11:1414"
        echo "   • Via túnel SSH:    localhost:1414"
        echo "   • Requiere VPN:     '$VPN_NAME' en $MAC_HOST"
        echo ""
        echo "💡 NOTA: El script siempre pedirá la contraseña interactivamente"
        echo "          para mayor seguridad."
        ;;
esac
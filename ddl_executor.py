#!/usr/bin/env python3
"""
DDL Executor - Herramienta segura para ejecutar operaciones DDL
==============================================================

Este script permite ejecutar operaciones DDL (ALTER, CREATE, DROP, etc.)
SOLO CON CONFIRMACIÓN EXPLÍCITA del usuario.

IMPORTANTE:
- ⚠️  SOLO para operaciones que modifican estructura (no datos)
- ✅ Requiere confirmación antes de cada operación
- ✅ Registra todas las operaciones en log
- ✅ Validaciones de seguridad incluidas

Uso:
    python ddl_executor.py -c proyectos_prod --sql "ALTER VIEW ..."
    python ddl_executor.py -c proyectos_prod --file schema.sql
"""

import argparse
import sys
import json
import os
from datetime import datetime
import re

def get_db_config():
    """Cargar configuración de base de datos"""
    import yaml
    
    config_path = os.path.join(os.path.dirname(__file__), "collections.yaml")
    secrets_path = os.path.join(os.path.dirname(__file__), "collections.secrets.yaml")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    with open(secrets_path, 'r') as f:
        secrets = yaml.safe_load(f)
    
    return config, secrets


def get_connection_config(collection_name):
    """Obtener configuración de conexión para una colección"""
    config, secrets = get_db_config()
    
    if collection_name not in config['collections']:
        print(f"❌ Colección '{collection_name}' no encontrada")
        sys.exit(1)
    
    col_config = config['collections'][collection_name]
    sources = col_config['sources']
    
    if not sources:
        print(f"❌ Colección '{collection_name}' no tiene fuentes")
        sys.exit(1)
    
    sql_config = sources[0]['sql_enrich'].copy()
    
    # Cargar credenciales
    col_secrets = secrets.get('collections', {}).get(collection_name, {})
    if col_secrets:
        for source_secret in col_secrets.get('sources', []):
            if 'sql_enrich' in source_secret:
                sql_config['user'] = source_secret['sql_enrich']['user']
                sql_config['password'] = source_secret['sql_enrich']['password']
                break
    
    return sql_config


def validate_ddl(sql):
    """Validar que es operación DDL permitida"""
    # Operaciones permitidas
    allowed_patterns = [
        r'^\s*ALTER\s+VIEW\s+',
        r'^\s*CREATE\s+VIEW\s+',
        r'^\s*DROP\s+VIEW\s+',
        r'^\s*ALTER\s+TABLE\s+',
        r'^\s*CREATE\s+TABLE\s+',
    ]
    
    # Operaciones prohibidas (por seguridad)
    forbidden_patterns = [
        r'\bDROP\s+DATABASE\b',
        r'\bTRUNCATE\b',
        r'\bDELETE\s+FROM\b',
        r'\bINSERT\s+INTO\b',
        r'\bUPDATE\s+\b',
    ]
    
    sql_clean = sql.strip().upper()
    
    # Validar que es operación permitida
    is_allowed = any(re.match(p, sql_clean) for p in allowed_patterns)
    
    if not is_allowed:
        print("❌ Operación NO permitida")
        print("   Operaciones soportadas: ALTER/CREATE/DROP VIEW, ALTER/CREATE TABLE")
        return False
    
    # Validar que no contiene operaciones prohibidas
    if any(re.search(p, sql_clean) for p in forbidden_patterns):
        print("❌ Operación prohibida por seguridad")
        return False
    
    return True


def format_sql_for_display(sql):
    """Formatear SQL para mostrar al usuario"""
    lines = sql.split('\n')
    formatted = []
    for i, line in enumerate(lines, 1):
        formatted.append(f"  {i:3d} | {line}")
    return '\n'.join(formatted)


def log_operation(collection, sql, status, error=None):
    """Registrar operación DDL en log"""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'ddl_operations.log')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'collection': collection,
        'status': status,
        'operation': sql[:100] + ('...' if len(sql) > 100 else ''),
        'error': error
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    return log_file


def confirm_operation(sql, collection):
    """Pedir confirmación explícita del usuario"""
    print("\n" + "="*70)
    print("⚠️  ADVERTENCIA: Operación DDL en PRODUCCIÓN")
    print("="*70)
    print(f"\nColección: {collection}")
    print(f"\nSQL a ejecutar:")
    print(format_sql_for_display(sql))
    print("\n" + "="*70)
    print("\n⚠️  ESTA OPERACIÓN MODIFICA LA ESTRUCTURA DE LA BASE DE DATOS")
    print("   • No se puede deshacer automáticamente")
    print("   • Afectará a todos los usuarios de la BD")
    print("   • Será registrada en auditoría")
    print("\n" + "="*70)
    
    confirmation = input("\n¿Ejecutar esta operación? (escribir 'CONFIRMO' para continuar): ").strip()
    
    if confirmation != "CONFIRMO":
        print("\n❌ Operación cancelada")
        return False
    
    return True


def execute_ddl(collection_name, sql):
    """Ejecutar operación DDL"""
    from db_connector import get_connection
    
    # Validar SQL
    if not validate_ddl(sql):
        return False
    
    # Pedir confirmación
    if not confirm_operation(sql, collection_name):
        return False
    
    # Obtener configuración de conexión
    sql_config = get_connection_config(collection_name)
    
    # Ejecutar
    print("\n⏳ Ejecutando operación DDL...")
    try:
        conn = get_connection(sql_config)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        conn.close()
        
        print("✅ Operación completada exitosamente")
        log_file = log_operation(collection_name, sql, 'SUCCESS')
        print(f"📝 Registrado en: {log_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error al ejecutar operación: {e}")
        log_file = log_operation(collection_name, sql, 'FAILED', str(e))
        print(f"📝 Error registrado en: {log_file}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Ejecutor DDL seguro con confirmación explícita",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("-c", "--collection", required=True, help="Colección (ej: proyectos_prod)")
    parser.add_argument("--sql", help="Operación DDL a ejecutar")
    parser.add_argument("--file", help="Archivo con operación DDL")
    
    args = parser.parse_args()
    
    # Validar que se proporcionó SQL o archivo
    if not args.sql and not args.file:
        print("❌ Debes proporcionar --sql o --file")
        parser.print_help()
        sys.exit(1)
    
    # Obtener SQL
    if args.sql:
        sql = args.sql
    else:
        with open(args.file, 'r') as f:
            sql = f.read()
    
    # Ejecutar
    success = execute_ddl(args.collection, sql)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

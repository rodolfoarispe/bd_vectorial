#!/usr/bin/env python3
"""
Script simple para consultas SQL directas a producción GECA
=========================================================
Requiere que el túnel SSH esté activo: ./scripts/geca_prod.sh start

Uso:
    python query_prod.py "SELECT * FROM temp_sage_chart LIMIT 10"
    python query_prod.py "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='VIEW'" --limit 50
"""

import sys
import argparse
import yaml
import os
from db_connector import execute_query


def load_prod_config():
    """Cargar configuración de producción desde collections.yaml + secrets"""
    
    # Cargar configuración base
    config_path = os.path.join(os.path.dirname(__file__), "collections.yaml")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Cargar secrets
    secrets_path = os.path.join(os.path.dirname(__file__), "collections.secrets.yaml")
    with open(secrets_path, 'r') as f:
        secrets = yaml.safe_load(f)
    
    # Configurar conexión a producción
    sql_config = config['collections']['proyectos_prod']['sources'][0]['sql_enrich'].copy()
    sql_config['user'] = secrets['collections']['proyectos_prod']['sources'][0]['sql_enrich']['user']
    sql_config['password'] = secrets['collections']['proyectos_prod']['sources'][0]['sql_enrich']['password']
    
    return sql_config


def main():
    parser = argparse.ArgumentParser(
        description="Consultas SQL directas a producción GECA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("query", help="Consulta SQL a ejecutar")
    parser.add_argument("--limit", type=int, default=100, help="Límite de filas (default: 100)")
    
    args = parser.parse_args()
    
    try:
        sql_config = load_prod_config()
        
        print(f"Ejecutando consulta (límite: {args.limit} filas)...")
        print(f"SQL: {args.query}")
        print("=" * 60)
        
        df = execute_query(sql_config, args.query, max_rows=args.limit)
        
        if len(df) == 0:
            print("0 filas devueltas")
        else:
            print(f"\n=== RESULTADOS ({len(df)} filas) ===\n")
            print(df.to_string(index=False))
            
            if len(df) == args.limit:
                print(f"\n⚠️  Resultados limitados a {args.limit} filas. Usa --limit para cambiar.")
                
    except FileNotFoundError as e:
        print(f"Error: Archivo de configuración no encontrado: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
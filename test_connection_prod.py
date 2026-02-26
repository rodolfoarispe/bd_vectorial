#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_collection_config
from db_connector import execute_query

def main():
    """Probar conectividad básica a producción"""
    
    try:
        # Obtener configuración de colección proyectos_prod
        cfg = get_collection_config("proyectos_prod")
        
        # Obtener la fuente con sql_enrich
        source = next((s for s in cfg.get("sources", []) if s.get("sql_enrich")), None)
        if not source:
            print("❌ No se encontró configuración sql_enrich en proyectos_prod")
            return
            
        sql_enrich = source.get("sql_enrich")
        
        print(f"🔍 Probando conectividad a producción...")
        print(f"📡 Servidor: {sql_enrich['server']}:{sql_enrich['port']}")
        print(f"💾 Base de datos: {sql_enrich['database']}")
        print(f"👤 Usuario: {sql_enrich['user']}")
        print()
        
        # Prueba simple de conectividad
        sql = "SELECT COUNT(*) as total_tables FROM INFORMATION_SCHEMA.TABLES"
        
        print("📝 SQL Query (test):")
        print(sql)
        print()
        
        # Ejecutar consulta con timeout corto
        df = execute_query(sql_enrich, sql, max_rows=1)
        
        print(f"✅ Conectividad exitosa!")
        print(f"📊 Total tablas en BD: {df.iloc[0]['total_tables']}")
        
        # Verificar si existe la vista vi_sage_jobs_facturas
        sql2 = """
        SELECT COUNT(*) as existe 
        FROM INFORMATION_SCHEMA.VIEWS 
        WHERE TABLE_NAME = 'vi_sage_jobs_facturas'
        """
        
        df2 = execute_query(sql_enrich, sql2, max_rows=1)
        existe_vista = df2.iloc[0]['existe'] > 0
        
        if existe_vista:
            print("✅ La vista vi_sage_jobs_facturas existe")
            
            # Contar registros en la vista
            sql3 = "SELECT COUNT(*) as total_registros FROM dbo.vi_sage_jobs_facturas"
            df3 = execute_query(sql_enrich, sql3, max_rows=1)
            print(f"📊 Total registros en vista: {df3.iloc[0]['total_registros']}")
            
        else:
            print("❌ La vista vi_sage_jobs_facturas NO existe en producción")
            print("📋 Tablas temp_sage disponibles:")
            
            sql4 = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME LIKE 'temp_sage%' 
            ORDER BY TABLE_NAME
            """
            df4 = execute_query(sql_enrich, sql4, max_rows=20)
            for i, row in df4.iterrows():
                print(f"  - {row['TABLE_NAME']}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_collection_config
from db_connector import execute_query

def main():
    """Ejecutar consulta a vista de jobs y facturas Sage en producción"""
    
    try:
        # Obtener configuración de colección proyectos_prod (incluye secrets merged)
        cfg = get_collection_config("proyectos_prod")
        
        # Obtener la fuente con sql_enrich
        source = next((s for s in cfg.get("sources", []) if s.get("sql_enrich")), None)
        if not source:
            print("❌ No se encontró configuración sql_enrich en proyectos_prod")
            return
            
        sql_enrich = source.get("sql_enrich")
        
        print(f"🔍 Ejecutando consulta en producción...")
        print(f"📡 Servidor: {sql_enrich['server']}:{sql_enrich['port']}")
        print(f"💾 Base de datos: {sql_enrich['database']}")
        print()
        
        # Consulta SQL
        sql = """
        SELECT TOP 100
            jobid,
            jobdescription,
            factura,
            fecha_factura,
            descripcion_modulo,
            monto_factura,
            estado_pago,
            ingresos,
            gastos,
            cliente_proveedor_id,
            descripcion_transaccion
        FROM dbo.vi_sage_jobs_facturas 
        WHERE fecha_factura >= '2026-01-01' 
          AND fecha_factura < '2026-02-01'
        ORDER BY fecha_factura DESC, jobid;
        """
        
        print("📝 SQL Query:")
        print(sql.strip())
        print()
        
        # Ejecutar consulta
        df = execute_query(sql_enrich, sql, max_rows=100)
        
        print(f"📊 Resultados encontrados: {len(df)} registros")
        print()
        
        if len(df) > 0:
            # Mostrar primeros registros
            print("🔍 JOBS Y FACTURAS SAGE - ENERO 2026:")
            print("=" * 80)
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                print(f"Job: {row['jobid']} - {str(row['jobdescription'])[:50]}...")
                print(f"  Factura: {row['factura']} | Fecha: {row['fecha_factura']}")
                print(f"  Tipo: {row['descripcion_modulo']} | Estado: {row['estado_pago']}")
                print(f"  Monto: ${float(row['monto_factura']):,.2f} | Cliente/Prov: {row['cliente_proveedor_id']}")
                print(f"  Descripción: {str(row['descripcion_transaccion'])[:60]}...")
                print()
            
            if len(df) > 10:
                print(f"... y {len(df) - 10} registros más")
                print()
            
            # Resumen estadístico
            total_ingresos = df['ingresos'].sum()
            total_gastos = df['gastos'].sum()
            jobs_unicos = df['jobid'].nunique()
            facturas_pagadas = len(df[df['estado_pago'] == 'PAGADA'])
            facturas_pendientes = len(df[df['estado_pago'] == 'PENDIENTE'])
            
            print("📈 RESUMEN ESTADÍSTICO:")
            print(f"  • Total jobs únicos: {jobs_unicos}")
            print(f"  • Total facturas: {len(df)}")
            print(f"  • Facturas pagadas: {facturas_pagadas}")
            print(f"  • Facturas pendientes: {facturas_pendientes}")
            print(f"  • Total ingresos: ${total_ingresos:,.2f}")
            print(f"  • Total gastos: ${total_gastos:,.2f}")
            print(f"  • Utilidad bruta: ${(total_ingresos - total_gastos):,.2f}")
            
        else:
            print("⚠️  No se encontraron registros para enero 2026")
            print("Posibles causas:")
            print("  - La vista vi_sage_jobs_facturas no existe en producción")  
            print("  - No hay datos para el período especificado")
            print("  - Problema de conectividad con la base de datos")
    
    except Exception as e:
        print(f"❌ Error ejecutando consulta: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
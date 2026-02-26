#!/usr/bin/env python3
import pyodbc
import pandas as pd
import sys

def query_jobs_facturas():
    """Consulta jobs y facturas de Sage para enero 2026"""
    
    # Conectar a GECA producción via túnel
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost,1414;DATABASE=analitica;UID=analitica;PWD=biuser20!;TrustServerCertificate=yes'

    try:
        conn = pyodbc.connect(conn_str)
        
        # Consulta a la vista de jobs y facturas de enero 2026
        query = """
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
        
        # Ejecutar consulta
        df = pd.read_sql_query(query, conn)
        print(f'📊 Resultados encontrados: {len(df)} registros')
        print('')
        
        if len(df) > 0:
            # Mostrar primeros registros
            print('🔍 JOBS Y FACTURAS SAGE - ENERO 2026 (Primeros registros):')
            print('=' * 80)
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                print(f'Job: {row["jobid"]} - {row["jobdescription"]}')
                print(f'  Factura: {row["factura"]} | Fecha: {row["fecha_factura"]}')
                print(f'  Tipo: {row["descripcion_modulo"]} | Estado: {row["estado_pago"]}')
                print(f'  Monto: ${row["monto_factura"]:,.2f} | Cliente/Prov: {row["cliente_proveedor_id"]}')
                print(f'  Descripción: {row["descripcion_transaccion"]}')
                print('')
            
            # Resumen estadístico
            total_ingresos = df['ingresos'].sum()
            total_gastos = df['gastos'].sum()
            jobs_unicos = df['jobid'].nunique()
            facturas_pagadas = len(df[df['estado_pago'] == 'PAGADA'])
            facturas_pendientes = len(df[df['estado_pago'] == 'PENDIENTE'])
            
            print('📈 RESUMEN ESTADÍSTICO:')
            print(f'  • Total jobs únicos: {jobs_unicos}')
            print(f'  • Total facturas: {len(df)}')
            print(f'  • Facturas pagadas: {facturas_pagadas}')
            print(f'  • Facturas pendientes: {facturas_pendientes}')
            print(f'  • Total ingresos: ${total_ingresos:,.2f}')
            print(f'  • Total gastos: ${total_gastos:,.2f}')
            print(f'  • Utilidad bruta: ${(total_ingresos - total_gastos):,.2f}')
            
        else:
            print('⚠️  No se encontraron registros para enero 2026')
            print('Verificando si la vista existe...')
            
            # Verificar si la vista existe
            check_query = """
            SELECT COUNT(*) as total 
            FROM INFORMATION_SCHEMA.VIEWS 
            WHERE TABLE_NAME = 'vi_sage_jobs_facturas'
            """
            check_df = pd.read_sql_query(check_query, conn)
            if check_df.iloc[0]['total'] == 0:
                print('❌ La vista vi_sage_jobs_facturas no existe en producción')
            else:
                print('✅ La vista existe, pero sin datos para enero 2026')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        return False
        
    return True

if __name__ == "__main__":
    query_jobs_facturas()
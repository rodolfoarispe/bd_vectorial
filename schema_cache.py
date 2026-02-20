"""
Generador de caché literal de esquemas desde sql_enrich.
Se ejecuta automáticamente al indexar una colección.
"""

import json
import os
from pathlib import Path
from config import get_collection_config
from db_connector import fetch_table_schema
import pandas as pd


def generate_schemas_cache(collection_name: str, output_path: str = None):
    """
    Genera/refresca el caché de esquemas para las tablas documentadas en una colección.
    
    Se ejecuta automáticamente al indexar. Los esquemas se extraen de sql_enrich
    (sin embeddings, búsqueda literal).
    
    Args:
        collection_name: Nombre de la colección
        output_path: Ruta del archivo JSON de salida (default: data/schemas_cache.json)
    """
    
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "data", "schemas_cache.json")
    
    # Obtener configuración de la colección
    cfg = get_collection_config(collection_name)
    
    # Buscar la fuente con sql_enrich
    source = next((s for s in cfg.get("sources", []) if s.get("sql_enrich")), None)
    if not source:
        print(f"  ⚠️  Sin sql_enrich configurado; se omite generación de caché de esquemas")
        return
    
    sql_enrich = source.get("sql_enrich")
    max_columns = sql_enrich.get("max_columns", 200)
    
    # Leer CSV para obtener las tablas documentadas
    csv_path = source.get("path")
    if not csv_path or not os.path.isfile(csv_path):
        print(f"  ⚠️  CSV no encontrado: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    
    # Extraer esquemas de las tablas mencionadas
    schemas = {}
    for _, row in df.iterrows():
        tabla = row.get("tabla")
        if not tabla or pd.isna(tabla):
            continue
        
        tabla_str = str(tabla).strip()
        if tabla_str in schemas:
            continue  # Ya indexada
        
        try:
            cols = fetch_table_schema(sql_enrich, tabla_str, max_columns=max_columns)
            schemas[tabla_str] = cols
            print(f"  ✓ {tabla_str}: {len(cols)} columnas")
        except Exception as e:
            print(f"  ✗ {tabla_str}: {e}")
    
    # Guardar como JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schemas, f, indent=2, ensure_ascii=False)
    
    print(f"\n  Caché de esquemas: {len(schemas)} tabla(s) en {output_path}")

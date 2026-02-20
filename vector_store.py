import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import pandas as pd
from config import get_chroma_config
from embeddings import get_embeddings_batch
from db_connector import fetch_distinct_values, fetch_table_schema
import re


def get_chroma_client():
    cfg = get_chroma_config()
    return chromadb.PersistentClient(
        path=cfg["persist_directory"],
        settings=Settings(anonymized_telemetry=False)
    )


def get_or_create_collection(collection_name):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def prepare_document(row: pd.Series, vectorize_columns: List[str]) -> str:
    parts = []
    for col in vectorize_columns:
        value = row.get(col)
        if value and str(value).strip() and str(value).lower() not in ["none", "nan"]:
            parts.append(f"{col}: {value}")
    return " | ".join(parts) if parts else "sin información"


def prepare_metadata(row: pd.Series, metadata_columns: List[str], source_name: str) -> Dict[str, Any]:
    metadata = {"_source": source_name}
    for col in metadata_columns:
        value = row.get(col)
        if value is not None and str(value).lower() not in ["none", "nan", "nat"]:
            if isinstance(value, (int, float, bool)):
                metadata[col] = value
            else:
                metadata[col] = str(value)
    return metadata


def _split_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value)
    parts = re.split(r"[;,]", text)
    return [p.strip() for p in parts if p.strip()]


def index_source(df: pd.DataFrame, collection_name: str, source_config: dict, batch_size: int = 100):
    """Indexa los datos de un source en la colección."""
    source_name = source_config["name"]
    vectorize_cols = source_config["vectorize"]
    metadata_cols = source_config["metadata"]

    collection = get_or_create_collection(collection_name)

    print(f"  Preparando documentos de '{source_name}'...")
    documents = [prepare_document(row, vectorize_cols) for _, row in df.iterrows()]
    metadatas = [prepare_metadata(row, metadata_cols, source_name) for _, row in df.iterrows()]

    # IDs únicos: source_name + id o índice
    if "id" in df.columns:
        ids = [f"{source_name}_{row['id']}" for _, row in df.iterrows()]
    else:
        ids = [f"{source_name}_{i}" for i in range(len(df))]

    sql_enrich = source_config.get("sql_enrich")
    if sql_enrich:
        max_values = int(sql_enrich.get("max_values", 50))
        include_schema = bool(sql_enrich.get("include_schema", False))
        max_columns = int(sql_enrich.get("max_columns", 200))
        extra_documents = []
        extra_metadatas = []
        extra_ids = []
        distinct_cache = {}
        schema_cache = {}
        schema_added = set()

        print(f"  Enriqueciendo con catalogos (max {max_values} valores)...")
        for idx, row in df.iterrows():
            table = row.get("tabla") or row.get("table")
            dims_raw = row.get("dimensiones") or row.get("dimensions")
            dims = _split_list(dims_raw)
            if not table or not dims:
                table = None if not table else str(table)
            rule_id = row.get("id", idx)

            if include_schema and table:
                schema_key = str(table)
                if (rule_id, schema_key) not in schema_added:
                    if schema_key not in schema_cache:
                        try:
                            schema_cache[schema_key] = fetch_table_schema(
                                sql_enrich, schema_key, max_columns=max_columns
                            )
                        except Exception as e:
                            print(f"    Esquema omitido {schema_key}: {e}")
                            schema_cache[schema_key] = []
                    schema_cols = schema_cache.get(schema_key, [])
                    if schema_cols:
                        doc = f"Esquema {schema_key}: {', '.join(schema_cols)}"
                        extra_documents.append(doc)
                        extra_ids.append(f"{source_name}_{rule_id}_schema_{schema_key}")
                        meta = {
                            "_source": source_name,
                            "kind": "schema",
                            "rule_id": str(rule_id),
                            "tabla": schema_key
                        }
                        for key in ("cliente", "proyecto", "entidad"):
                            value = row.get(key)
                            if value is not None and str(value).strip() != "":
                                meta[key] = str(value)
                        extra_metadatas.append(meta)
                    schema_added.add((rule_id, schema_key))

            if not table or not dims:
                continue
            for dim in dims:
                cache_key = (str(table), str(dim))
                if cache_key not in distinct_cache:
                    try:
                        distinct_cache[cache_key] = fetch_distinct_values(
                            sql_enrich, str(table), str(dim), limit=max_values
                        )
                    except Exception as e:
                        print(f"    Catalogo omitido {table}.{dim}: {e}")
                        distinct_cache[cache_key] = []
                values = distinct_cache[cache_key]
                if not values:
                    continue

                doc = f"Catalogo {table}.{dim}: {', '.join(values)}"
                extra_documents.append(doc)
                extra_ids.append(f"{source_name}_{rule_id}_catalog_{table}_{dim}")

                meta = {
                    "_source": source_name,
                    "kind": "catalog",
                    "rule_id": str(rule_id),
                    "tabla": str(table),
                    "columna": str(dim)
                }
                for key in ("cliente", "proyecto", "entidad"):
                    value = row.get(key)
                    if value is not None and str(value).strip() != "":
                        meta[key] = str(value)
                extra_metadatas.append(meta)

        if extra_documents:
            print(f"  Catalogos generados: {len(extra_documents)}")
            documents.extend(extra_documents)
            metadatas.extend(extra_metadatas)
            ids.extend(extra_ids)

    print(f"  Generando embeddings para '{source_name}'...")
    total = len(documents)

    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)

        batch_embeddings = get_embeddings_batch(documents[i:end], show_progress=False)

        collection.add(
            ids=ids[i:end],
            embeddings=batch_embeddings,
            documents=documents[i:end],
            metadatas=metadatas[i:end]
        )

        print(f"  Indexados: {end}/{total} ({end / total * 100:.1f}%)")

    print(f"  '{source_name}' completado: {total} documentos")


def get_collection_stats(collection_name):
    collection = get_or_create_collection(collection_name)
    return {
        "collection_name": collection_name,
        "total_documents": collection.count()
    }


def clear_collection(collection_name):
    client = get_chroma_client()
    try:
        client.delete_collection(collection_name)
        print(f"Colección '{collection_name}' eliminada")
    except Exception:
        print(f"La colección '{collection_name}' no existía")

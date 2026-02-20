from typing import List, Dict, Any, Optional
from vector_store import get_or_create_collection
from embeddings import get_embedding
from config import get_collection_config


def _build_schema_description(collection_name: str) -> str:
    """Genera una descripción del esquema de la colección para el prompt."""
    cfg = get_collection_config(collection_name)
    parts = [f"Colección: {collection_name}"]
    for source in cfg["sources"]:
        name = source["name"]
        stype = source["type"]
        vectorize = source.get("vectorize", [])
        metadata = source.get("metadata", [])
        all_cols = list(dict.fromkeys(vectorize + metadata))
        parts.append(f"\nFuente: {name} (tipo: {stype})")
        if stype in ("mssql", "mariadb", "duckdb"):
            parts.append(f"  Servidor: {source.get('server', source.get('path', ''))}")
            parts.append(f"  Base de datos: {source.get('database', '')}")
        if "query" in source:
            parts.append(f"  Query original: {source['query'].strip()}")
        if stype == "csv":
            parts.append(f"  Archivo: {source.get('path', '')}")
        parts.append(f"  Columnas: {', '.join(all_cols)}")
        parts.append(f"  Campos de búsqueda semántica: {', '.join(vectorize)}")
        parts.append(f"  Campos de filtro/metadata: {', '.join(metadata)}")
    return "\n".join(parts)


def search(
        query: str,
        collection_name: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Búsqueda híbrida: semántica (vectorial) + filtros (metadata).

    Args:
        query: Texto de búsqueda
        collection_name: Nombre de la colección
        n_results: Número de resultados
        filters: Filtros sobre metadata (ej: {"Status": "Delivered"})
    """
    collection = get_or_create_collection(collection_name)

    query_embedding = get_embedding(query)

    where = filters if filters else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    formatted = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        similarity = max(0, 1 - distance)

        formatted.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": distance,
            "similarity": similarity
        })

    return formatted


def _build_prompt(query: str, collection_name: str, results: List[Dict[str, Any]]) -> str:
    """Arma el prompt RAG con esquema + contexto + pregunta."""
    schema = _build_schema_description(collection_name)

    context_parts = []
    for r in results:
        source = r["metadata"].get("_source", "desconocido")
        meta_str = " | ".join(f"{k}: {v}" for k, v in r["metadata"].items() if k != "_source")
        context_parts.append(f"[Fuente: {source}] {r['document']}")
        if meta_str:
            context_parts.append(f"  Metadata: {meta_str}")

    context = "\n".join(context_parts)

    return f"""Eres un asistente experto sobre los datos de esta base de datos. Tienes acceso al esquema de las tablas y a registros relevantes encontrados por búsqueda semántica.

Esquema de datos:
{schema}

Registros relevantes:
{context}

Responde la pregunta del usuario basándote en el esquema y los datos proporcionados. Si no hay información suficiente, dilo. Responde en español de forma clara y concisa.

Pregunta: {query}

Respuesta:"""


def ask(query: str, collection_name: str, n_results: int = 5, filters: Optional[Dict[str, Any]] = None) -> str:
    """
    RAG: busca contexto relevante y genera respuesta en lenguaje natural.
    """
    import requests
    from config import get_ollama_config

    cfg = get_ollama_config()

    results = search(query, collection_name, n_results=n_results, filters=filters)

    if not results:
        return "No encontré información relevante para responder."

    prompt = _build_prompt(query, collection_name, results)

    response = requests.post(
        f"{cfg['base_url']}/api/generate",
        json={
            "model": cfg["chat_model"],
            "prompt": prompt,
            "stream": False
        }
    )

    if response.status_code != 200:
        raise Exception(f"Error de Ollama: {response.text}")

    return response.json()["response"]


def ask_stream(query: str, collection_name: str, n_results: int = 5, filters: Optional[Dict[str, Any]] = None):
    """
    RAG con streaming: busca contexto y genera respuesta token a token.
    """
    import requests
    from config import get_ollama_config

    cfg = get_ollama_config()

    results = search(query, collection_name, n_results=n_results, filters=filters)

    if not results:
        yield "No encontré información relevante para responder."
        return

    prompt = _build_prompt(query, collection_name, results)

    response = requests.post(
        f"{cfg['base_url']}/api/generate",
        json={
            "model": cfg["chat_model"],
            "prompt": prompt,
            "stream": True
        },
        stream=True
    )

    if response.status_code != 200:
        yield f"Error de Ollama: {response.text}"
        return

    for line in response.iter_lines():
        if line:
            import json
            data = json.loads(line)
            token = data.get("response", "")
            if token:
                yield token
            if data.get("done", False):
                break


def _get_sql_sources(collection_name: str) -> List[Dict[str, Any]]:
    """Retorna las fuentes con mode: sql de la colección."""
    cfg = get_collection_config(collection_name)
    return [s for s in cfg["sources"] if s.get("mode") == "sql"]


def _build_sql_schema(collection_name: str) -> str:
    """Genera descripción del esquema SQL para el prompt de generación de consultas."""
    sql_sources = _get_sql_sources(collection_name)
    if not sql_sources:
        return ""
    parts = []
    for source in sql_sources:
        db_type = source["type"]
        table = source.get("table", source["name"])
        columns = source.get("columns", [])
        parts.append(f"Motor: {db_type}")
        parts.append(f"Tabla: {table}")
        parts.append("Columnas:")
        for col in columns:
            parts.append(f"  - {col}")
    return "\n".join(parts)


def _extract_sql(text: str):
    """Extrae SQL de un bloque ```sql ... ```."""
    import re
    match = re.search(r'```sql\s*\n?(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _find_sql_source(collection_name: str, sql: str):
    """Busca el source SQL cuya tabla aparece en la consulta."""
    import re
    sql_sources = _get_sql_sources(collection_name)
    for source in sql_sources:
        table = source.get("table", source["name"])
        if re.search(r'\b' + re.escape(table) + r'\b', sql, re.IGNORECASE):
            return source
    # Fallback: primer source SQL disponible
    return sql_sources[0] if sql_sources else None


def chat_stream(query: str, collection_name: str, n_results: int = 5,
                filters: Optional[Dict[str, Any]] = None, status_callback=None,
                force_sql: bool = False):
    """
    Asistente SQL + RAG con streaming.

    force_sql=True: genera SQL, ejecuta, interpreta (comando /sql).
    force_sql=False: busca en ChromaDB y responde con conocimiento (RAG).
    """
    import json
    import requests
    from config import get_ollama_config

    cfg = get_ollama_config()

    if force_sql:
        yield from _sql_path(query, collection_name, cfg, status_callback)
    else:
        yield from _rag_path(query, collection_name, n_results, filters, cfg, status_callback)


def _sql_path(query, collection_name, cfg, status_callback):
    """Genera SQL, ejecuta, interpreta resultados."""
    import json
    import requests
    from db_connector import execute_query

    sql_schema = _build_sql_schema(collection_name)

    if status_callback:
        status_callback("thinking")

    prompt1 = f"""Genera una consulta SQL para responder esta pregunta.

{sql_schema}

Ejemplos de sintaxis MSSQL:
- SELECT TOP 10 Number, Status FROM temp_shipment_master ORDER BY CreatedOn DESC
- SELECT CarrierName, COUNT(*) AS total FROM temp_shipment_master GROUP BY CarrierName ORDER BY total DESC

Genera SOLO el SQL dentro de ```sql ... ```. Usa SOLO columnas del esquema arriba. Sintaxis MSSQL (TOP en vez de LIMIT).

Pregunta: {query}
"""

    response1 = requests.post(
        f"{cfg['base_url']}/api/generate",
        json={"model": cfg["chat_model"], "prompt": prompt1, "stream": False}
    )

    if response1.status_code != 200:
        yield f"Error de Ollama: {response1.text}"
        return

    first_response = response1.json()["response"]
    sql = _extract_sql(first_response)

    if not sql:
        yield f"No se pudo generar SQL.\n\nRespuesta del modelo:\n{first_response}"
        return

    # Yield especial: el SQL para confirmación (main.py lo detecta)
    yield ("__SQL_CONFIRM__", sql)

    if status_callback:
        status_callback("executing")

    source = _find_sql_source(collection_name, sql)
    if not source:
        yield "No se encontró una fuente SQL configurada."
        return

    try:
        df = execute_query(source, sql)
    except Exception as e:
        yield f"Error ejecutando SQL: {e}\n\nSQL generado:\n{sql}"
        return

    result_text = df.to_string(index=False) if not df.empty else "(sin resultados)"
    row_count = len(df)

    # Guardar SQL y resultados en archivo
    import os
    log_path = os.path.join(os.path.dirname(__file__), "_resultado_sql.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Pregunta: {query}\n\n")
        f.write(f"SQL:\n{sql}\n\n")
        f.write(f"Resultados ({row_count} filas):\n{result_text}\n")

    # Interpretar resultados (streaming)
    if status_callback:
        status_callback("interpreting")

    prompt2 = f"""Resultados de: {sql}

{result_text}

Pregunta: {query}

Responde en español, claro y conciso. No muestres SQL.

Respuesta:"""

    response2 = requests.post(
        f"{cfg['base_url']}/api/generate",
        json={"model": cfg["chat_model"], "prompt": prompt2, "stream": True},
        stream=True
    )

    if response2.status_code != 200:
        yield f"Error de Ollama: {response2.text}"
        return

    for line in response2.iter_lines():
        if line:
            data = json.loads(line)
            token = data.get("response", "")
            if token:
                yield token
            if data.get("done", False):
                break


def _rag_path(query, collection_name, n_results, filters, cfg, status_callback):
    """Busca en ChromaDB y responde con conocimiento del negocio."""
    import json
    import requests

    if status_callback:
        status_callback("searching")
    results = search(query, collection_name, n_results=n_results, filters=filters)

    if not results:
        yield "No encontré información relevante para responder."
        return

    if status_callback:
        status_callback("answering")

    prompt = _build_prompt(query, collection_name, results)

    response = requests.post(
        f"{cfg['base_url']}/api/generate",
        json={"model": cfg["chat_model"], "prompt": prompt, "stream": True},
        stream=True
    )

    if response.status_code != 200:
        yield f"Error de Ollama: {response.text}"
        return

    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            token = data.get("response", "")
            if token:
                yield token
            if data.get("done", False):
                break


def print_results(results: List[Dict[str, Any]]):
    print(f"\n{'=' * 80}")
    print(f"Encontrados {len(results)} resultados")
    print(f"{'=' * 80}\n")

    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        print(f"[{i}] ID: {r['id']} | Similitud: {r['similarity']:.3f}")

        for key, value in meta.items():
            print(f"    {key}: {value}")

        doc = r["document"][:200] + "..." if len(r["document"]) > 200 else r["document"]
        print(f"    Documento: {doc}")
        print()

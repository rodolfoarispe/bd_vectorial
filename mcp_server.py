#!/usr/bin/env python3
"""MCP Server para consultar la base de datos vectorial desde Claude."""

import sys
import os

# Asegurar que el directorio del proyecto esté en el path
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bd-vectorial")


@mcp.tool()
def listar_colecciones() -> str:
    """Lista todas las colecciones disponibles con sus fuentes de datos."""
    from config import list_collections, get_collection_config

    cols = list_collections()
    lines = []
    for name in cols:
        cfg = get_collection_config(name)
        sources = cfg["sources"]
        source_names = [s["name"] for s in sources]
        lines.append(f"- {name}: fuentes = {', '.join(source_names)}")

    return f"Colecciones ({len(cols)}):\n" + "\n".join(lines)


@mcp.tool()
def buscar(coleccion: str, consulta: str, n_resultados: int = 5, fuente: str = None) -> str:
    """
    Búsqueda semántica en una colección vectorial.

    Args:
        coleccion: Nombre de la colección (ej: geca, mides)
        consulta: Texto de búsqueda en lenguaje natural
        n_resultados: Número de resultados a retornar (default 5)
        fuente: Filtrar por fuente específica (ej: shipments, conceptos). Opcional.
    """
    from search import search

    filters = {"_source": fuente} if fuente else None

    results = search(
        query=consulta,
        collection_name=coleccion,
        n_results=n_resultados,
        filters=filters
    )

    if not results:
        return "No se encontraron resultados."

    lines = []
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        source = meta.get("_source", "?")
        sim = r["similarity"]

        meta_str = " | ".join(f"{k}: {v}" for k, v in meta.items() if k != "_source")
        lines.append(f"[{i}] (similitud: {sim:.3f}, fuente: {source})")
        lines.append(f"    Documento: {r['document']}")
        if meta_str:
            lines.append(f"    Metadata: {meta_str}")
        lines.append("")

    return f"Resultados para '{consulta}':\n\n" + "\n".join(lines)


@mcp.tool()
def estadisticas(coleccion: str) -> str:
    """
    Muestra estadísticas de una colección.

    Args:
        coleccion: Nombre de la colección
    """
    from vector_store import get_collection_stats

    stats = get_collection_stats(coleccion)
    return f"Colección '{coleccion}': {stats['total_documents']:,} documentos indexados"


if __name__ == "__main__":
    mcp.run(transport="stdio")

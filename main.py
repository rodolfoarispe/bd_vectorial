#!/usr/bin/env python3
"""
Sistema de Base de Datos Vectorial Genérico
============================================
Indexa datos desde múltiples fuentes (MSSQL, MariaDB, DuckDB, CSV, JSON)
y permite búsquedas híbridas (semánticas + filtros) usando ChromaDB y Ollama.

Cada colección representa un cliente/proyecto y puede tener múltiples fuentes.

Uso:
    python main.py check                              # Verificar conexiones
    python main.py collections                        # Listar colecciones
    python main.py -c geca index                      # Indexar todas las fuentes
    python main.py -c geca index --source shipments   # Indexar solo una fuente
    python main.py -c geca index --limit 100          # Indexar con límite
    python main.py -c geca search "texto"             # Buscar en todo
    python main.py -c geca search "texto" -f _source=shipments  # Filtrar por fuente
    python main.py -c geca stats                      # Estadísticas
    python main.py -c geca interactive                # Modo interactivo
"""

import argparse
import sys


def cmd_check():
    from config import list_collections, get_collection_config
    from db_connector import test_source_connection
    from embeddings import test_ollama_connection

    print("Verificando conexiones...\n")

    ollama_ok = test_ollama_connection()
    all_ok = ollama_ok

    cols = list_collections()
    for col_name in cols:
        cfg = get_collection_config(col_name)
        print(f"\n[{col_name}]")
        for source in cfg["sources"]:
            print(f"  {source['name']}:")
            ok = test_source_connection(source)
            if not ok:
                all_ok = False

    print("\n" + "=" * 40)
    print(f"Ollama: {'OK' if ollama_ok else 'FALLO'}")
    print(f"Colecciones verificadas: {len(cols)}")
    print("=" * 40)

    return all_ok


def cmd_collections():
    from config import list_collections, get_collection_config

    cols = list_collections()
    print(f"\nColecciones disponibles ({len(cols)}):\n")

    for name in cols:
        cfg = get_collection_config(name)
        sources = cfg["sources"]
        print(f"  {name} ({len(sources)} fuentes):")
        for s in sources:
            stype = s["type"]
            label = s.get("server", s.get("path", ""))
            print(f"    - {s['name']} ({stype}://{label})")
        print()


def cmd_index(collection_name, source_name=None, limit=None, clear=False):
    from config import get_collection_config
    from db_connector import fetch_source
    from vector_store import index_source, clear_collection, get_collection_stats
    from schema_cache import generate_schemas_cache

    cfg = get_collection_config(collection_name)
    sources = cfg["sources"]

    if source_name:
        sources = [s for s in sources if s["name"] == source_name]
        if not sources:
            available = ", ".join(s["name"] for s in cfg["sources"])
            print(f"Error: Fuente '{source_name}' no encontrada. Disponibles: {available}")
            sys.exit(1)

    if clear:
        print(f"Limpiando colección '{collection_name}'...")
        clear_collection(collection_name)

    for source in sources:
        if source.get("mode") == "sql":
            print(f"\n  Saltando '{source['name']}' (mode: sql, no se indexa)")
            continue
        print(f"\nIndexando fuente '{source['name']}'...")
        df = fetch_source(source, limit=limit)
        index_source(df, collection_name, source)

    stats = get_collection_stats(collection_name)
    print(f"\nTotal en '{collection_name}': {stats['total_documents']:,} documentos")
    
    # Generar/refrescar caché de esquemas automáticamente
    print(f"\nGenerando caché de esquemas...")
    try:
        generate_schemas_cache(collection_name)
    except Exception as e:
        print(f"  ⚠️  Error al generar caché de esquemas: {e}")


def cmd_search(collection_name, query, n_results=10, filters=None):
    from search import search, print_results

    print(f"\nBuscando en '{collection_name}': '{query}'")
    if filters:
        print(f"  Filtros: {filters}")

    results = search(
        query=query,
        collection_name=collection_name,
        n_results=n_results,
        filters=filters
    )

    print_results(results)


def cmd_ask(collection_name, query, n_results=5, filters=None):
    from search import ask

    print(f"\nPregunta: {query}")
    if filters:
        print(f"  Filtros: {filters}")
    print()

    answer = ask(
        query=query,
        collection_name=collection_name,
        n_results=n_results,
        filters=filters
    )

    print(answer)


def cmd_stats(collection_name):
    from vector_store import get_collection_stats

    stats = get_collection_stats(collection_name)
    print(f"\nEstadísticas de '{collection_name}':")
    print(f"  Documentos indexados: {stats['total_documents']:,}")


def cmd_chat(collection_name):
    from config import get_collection_config
    from search import chat_stream

    cfg = get_collection_config(collection_name)
    rag_sources = [s["name"] for s in cfg["sources"] if s.get("mode") != "sql"]
    sql_sources = [s["name"] for s in cfg["sources"] if s.get("mode") == "sql"]

    STATUS_MESSAGES = {
        "searching": "  [1/3] Buscando contexto...",
        "thinking": "  [1/3] Analizando pregunta...",
        "executing": "  [2/3] Ejecutando SQL...",
        "interpreting": "  [3/3] Interpretando resultados...",
        "answering": "  [2/2] Generando respuesta...",
    }

    def show_status(status):
        msg = STATUS_MESSAGES.get(status, "")
        if msg:
            print(msg)

    print("\n" + "=" * 60)
    print(f"ASISTENTE SQL+RAG - {collection_name}")
    print("=" * 60)
    if sql_sources:
        print(f"  SQL: {', '.join(sql_sources)}")
    if rag_sources:
        print(f"  RAG: {', '.join(rag_sources)}")
    print("\nComandos:")
    print("  /sql pregunta        - Consultar datos via SQL")
    print("  /filter campo=valor  - Aplicar filtro")
    print("  /clear               - Limpiar filtros")
    print("  /filters             - Ver filtros activos")
    print("  /quit                - Salir")
    print("\nSin /sql responde con conocimiento (RAG).\n")

    filters = {}

    while True:
        try:
            query = input(">>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            break

        if not query:
            continue

        if query == "/quit":
            print("¡Hasta luego!")
            break

        elif query == "/clear":
            filters = {}
            print("Filtros limpiados")

        elif query == "/filters":
            print(f"Filtros activos: {filters if filters else '(ninguno)'}")

        elif query.startswith("/filter"):
            parts = query[7:].strip().split()
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    if value.lower() == "none":
                        filters.pop(key, None)
                    else:
                        filters[key] = value
            print(f"Filtros activos: {filters}")

        elif query.startswith("/sql"):
            sql_query = query[4:].strip()
            if not sql_query:
                print("Uso: /sql tu pregunta sobre datos")
                continue
            active_filters = filters if filters else None
            stream = chat_stream(sql_query, collection_name, filters=active_filters,
                                 status_callback=show_status, force_sql=True)
            cancelled = False
            for token in stream:
                if isinstance(token, tuple) and token[0] == "__SQL_CONFIRM__":
                    print(f"\n  SQL> {token[1]}")
                    confirm = input("  Ejecutar? (s/n): ").strip().lower()
                    if confirm != "s":
                        print("  Cancelado.")
                        cancelled = True
                        break
                    continue
                print(token, end="", flush=True)
            if not cancelled:
                print("\n")

        else:
            active_filters = filters if filters else None
            for token in chat_stream(query, collection_name, filters=active_filters,
                                     status_callback=show_status, force_sql=False):
                print(token, end="", flush=True)
            print("\n")


def cmd_schema(table_name):
    """Buscar esquema literal de una tabla (sin embeddings, búsqueda directa)."""
    import json
    import os

    cache_path = os.path.join(os.path.dirname(__file__), "data", "schemas_cache.json")
    
    if not os.path.isfile(cache_path):
        print(f"Error: Caché de esquemas no encontrado en {cache_path}")
        print("Ejecuta: python main.py -c <coleccion> index")
        sys.exit(1)
    
    with open(cache_path, "r", encoding="utf-8") as f:
        schemas = json.load(f)
    
    table_lower = table_name.lower()
    
    # Búsqueda exacta
    for tabla, cols in schemas.items():
        if tabla.lower() == table_lower:
            print(f"\nEsquema {tabla} ({len(cols)} columnas):\n")
            for col in cols:
                print(f"  {col}")
            return
    
    # Si no hay coincidencia exacta, sugerir similares
    print(f"\n✗ Tabla '{table_name}' no encontrada")
    print(f"\nTablas disponibles:")
    for tabla in sorted(schemas.keys()):
        print(f"  - {tabla}")
    sys.exit(1)


def cmd_interactive(collection_name):
    from config import get_collection_config
    from search import search, print_results

    cfg = get_collection_config(collection_name)
    source_names = [s["name"] for s in cfg["sources"]]

    print("\n" + "=" * 60)
    print(f"MODO INTERACTIVO - Colección: {collection_name}")
    print("=" * 60)
    print("\nComandos:")
    print("  /filter campo=valor  - Aplicar filtro")
    print("  /clear               - Limpiar filtros")
    print("  /filters             - Ver filtros activos")
    print("  /quit                - Salir")
    print(f"\nFuentes: {', '.join(source_names)}")
    print("Tip: usa /filter _source=shipments para filtrar por fuente")
    print("\nO escribe tu búsqueda semántica.\n")

    filters = {}

    while True:
        try:
            query = input("Buscar> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            break

        if not query:
            continue

        if query == "/quit":
            print("¡Hasta luego!")
            break

        elif query == "/clear":
            filters = {}
            print("Filtros limpiados")

        elif query == "/filters":
            print(f"Filtros activos: {filters if filters else '(ninguno)'}")

        elif query.startswith("/filter"):
            parts = query[7:].strip().split()
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    if value.lower() == "none":
                        filters.pop(key, None)
                    else:
                        filters[key] = value
            print(f"Filtros activos: {filters}")

        else:
            active_filters = filters if filters else None
            results = search(
                query=query,
                collection_name=collection_name,
                filters=active_filters
            )
            print_results(results)


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Base de Datos Vectorial Genérico",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("-c", "--collection", help="Nombre de la colección")

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    subparsers.add_parser("check", help="Verificar conexiones")
    subparsers.add_parser("collections", help="Listar colecciones")

    index_parser = subparsers.add_parser("index", help="Indexar datos")
    index_parser.add_argument("--source", help="Indexar solo esta fuente")
    index_parser.add_argument("--limit", type=int, help="Límite de registros por fuente")
    index_parser.add_argument("--clear", action="store_true", help="Limpiar colección antes de indexar")

    search_parser = subparsers.add_parser("search", help="Buscar en la colección")
    search_parser.add_argument("query", help="Texto de búsqueda")
    search_parser.add_argument("-n", "--n-results", type=int, default=10, help="Número de resultados")
    search_parser.add_argument("-f", "--filter", action="append", help="Filtro campo=valor (repetible)")

    ask_parser = subparsers.add_parser("ask", help="Preguntar en lenguaje natural (RAG)")
    ask_parser.add_argument("query", help="Pregunta en lenguaje natural")
    ask_parser.add_argument("-n", "--n-results", type=int, default=5, help="Resultados de contexto")
    ask_parser.add_argument("-f", "--filter", action="append", help="Filtro campo=valor (repetible)")

    schema_parser = subparsers.add_parser("schema", help="Consultar esquema de tabla (búsqueda literal)")
    schema_parser.add_argument("table", help="Nombre de la tabla")

    subparsers.add_parser("chat", help="Chat interactivo con RAG (como ollama run pero con BD vectorial)")
    subparsers.add_parser("stats", help="Mostrar estadísticas")
    subparsers.add_parser("interactive", help="Modo interactivo (búsqueda)")

    args = parser.parse_args()

    if args.command == "check":
        success = cmd_check()
        sys.exit(0 if success else 1)

    elif args.command == "collections":
        cmd_collections()

    elif args.command == "schema":
        cmd_schema(args.table)

    elif args.command in ("index", "search", "ask", "chat", "stats", "interactive"):
        if not args.collection:
            print("Error: Debes especificar una colección con -c/--collection")
            sys.exit(1)

        if args.command == "index":
            cmd_index(
                args.collection,
                source_name=args.source,
                limit=args.limit,
                clear=args.clear
            )

        elif args.command == "search":
            filters = {}
            if args.filter:
                for f in args.filter:
                    key, value = f.split("=", 1)
                    filters[key] = value
            cmd_search(
                args.collection,
                query=args.query,
                n_results=args.n_results,
                filters=filters if filters else None
            )

        elif args.command == "ask":
            filters = {}
            if args.filter:
                for f in args.filter:
                    key, value = f.split("=", 1)
                    filters[key] = value
            cmd_ask(
                args.collection,
                query=args.query,
                n_results=args.n_results,
                filters=filters if filters else None
            )

        elif args.command == "chat":
            cmd_chat(args.collection)

        elif args.command == "stats":
            cmd_stats(args.collection)

        elif args.command == "interactive":
            cmd_interactive(args.collection)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

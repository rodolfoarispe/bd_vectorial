import pymssql
import pandas as pd


def get_connection(source):
    """Crea conexión a BD según el tipo de motor y autenticación."""
    db_type = source["type"]

    if db_type == "mssql":
        return _connect_mssql(source)
    elif db_type == "mariadb":
        return _connect_mariadb(source)
    elif db_type == "duckdb":
        return _connect_duckdb(source)
    else:
        raise ValueError(f"Motor de BD no soportado: {db_type}")


def _connect_mssql(source):
    kwargs = {
        "server": source["server"],
        "port": source.get("port", 1433),
        "database": source["database"]
    }
    if source.get("auth") == "trusted":
        kwargs["conn_properties"] = "Trusted_Connection=Yes"
    else:
        kwargs["user"] = source["user"]
        kwargs["password"] = source["password"]
    return pymssql.connect(**kwargs)


def _connect_mariadb(source):
    import pymysql
    kwargs = {
        "host": source["server"],
        "port": source.get("port", 3306),
        "database": source["database"],
        "charset": "utf8mb4"
    }
    if source.get("auth") != "trusted":
        kwargs["user"] = source["user"]
        kwargs["password"] = source["password"]
    return pymysql.connect(**kwargs)


def _connect_duckdb(source):
    import duckdb
    path = source.get("path", ":memory:")
    return duckdb.connect(path, read_only=True)


def execute_query(source, sql, max_rows=50):
    """Ejecuta una consulta SELECT contra la BD y retorna un DataFrame."""
    import re
    normalized = sql.strip().lstrip("(")
    if not re.match(r'(?i)^SELECT\b', normalized):
        raise ValueError("Solo se permiten consultas SELECT")
    forbidden = re.compile(
        r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|EXEC|EXECUTE)\b',
        re.IGNORECASE
    )
    if forbidden.search(sql):
        raise ValueError("Consulta contiene operaciones no permitidas")
    conn = get_connection(source)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchmany(max_rows)
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()


def _validate_identifier(name: str) -> None:
    import re
    if not re.match(r"^[A-Za-z0-9_.]+$", name or ""):
        raise ValueError(f"Identificador SQL no permitido: {name}")


def _split_table_name(table: str):
    parts = (table or "").split(".")
    if len(parts) == 1:
        return None, parts[0]
    if len(parts) == 2:
        return parts[0], parts[1]
    raise ValueError(f"Nombre de tabla no permitido: {table}")


def _quote_identifier(db_type: str, name: str) -> str:
    parts = name.split(".")
    if db_type == "mssql":
        return ".".join(f"[{p}]" for p in parts)
    if db_type == "mariadb":
        return ".".join(f"`{p}`" for p in parts)
    return ".".join(f'"{p}"' for p in parts)


def build_distinct_query(source, table: str, column: str, limit: int) -> str:
    db_type = source["type"]
    _validate_identifier(table)
    _validate_identifier(column)
    table_q = _quote_identifier(db_type, table)
    column_q = _quote_identifier(db_type, column)
    if db_type == "mssql":
        return (
            f"SELECT DISTINCT TOP {limit} {column_q} "
            f"FROM {table_q} WHERE {column_q} IS NOT NULL"
        )
    return (
        f"SELECT DISTINCT {column_q} FROM {table_q} "
        f"WHERE {column_q} IS NOT NULL LIMIT {limit}"
    )


def fetch_distinct_values(source, table: str, column: str, limit: int = 50):
    sql = build_distinct_query(source, table, column, limit)
    df = execute_query(source, sql, max_rows=limit)
    if df.empty or column not in df.columns:
        return []
    values = []
    for value in df[column].dropna().tolist():
        if str(value).strip() == "":
            continue
        values.append(str(value))
    return values


def build_schema_query(source, table: str, max_columns: int):
    db_type = source["type"]
    schema, table_name = _split_table_name(table)
    _validate_identifier(table_name)
    if schema:
        _validate_identifier(schema)
    if db_type == "mssql":
        top = f"TOP {max_columns} " if max_columns else ""
        schema_clause = f" AND TABLE_SCHEMA = '{schema}'" if schema else ""
        return (
            f"SELECT {top}COLUMN_NAME, DATA_TYPE "
            f"FROM INFORMATION_SCHEMA.COLUMNS "
            f"WHERE TABLE_NAME = '{table_name}'{schema_clause} "
            f"ORDER BY ORDINAL_POSITION"
        )
    limit_clause = f" LIMIT {max_columns}" if max_columns else ""
    schema_clause = f" AND table_schema = '{schema}'" if schema else ""
    return (
        f"SELECT column_name, data_type "
        f"FROM information_schema.columns "
        f"WHERE table_name = '{table_name}'{schema_clause} "
        f"ORDER BY ordinal_position{limit_clause}"
    )


def fetch_table_schema(source, table: str, max_columns: int = 200):
    sql = build_schema_query(source, table, max_columns)
    df = execute_query(source, sql, max_rows=max_columns)
    if df.empty:
        return []

    def _get_ci(row, key):
        for k in row.index:
            if k.lower() == key.lower():
                return row[k]
        return None

    columns = []
    for _, row in df.iterrows():
        name = _get_ci(row, "column_name")
        dtype = _get_ci(row, "data_type")
        if name is None:
            continue
        if dtype is None:
            columns.append(str(name))
        else:
            columns.append(f"{name} ({dtype})")
    return columns


def fetch_source(source, limit=None):
    """Extrae datos de un source individual."""
    source_type = source["type"]

    if source_type in ("mssql", "mariadb", "duckdb"):
        return _fetch_sql(source, limit)
    elif source_type == "csv":
        return _fetch_csv(source["path"], limit)
    elif source_type == "json":
        return _fetch_json(source["path"], limit)
    else:
        raise ValueError(f"Tipo de fuente no soportado: {source_type}")


def _fetch_sql(source, limit=None):
    conn = get_connection(source)
    query = source["query"]

    if limit:
        db_type = source["type"]
        if db_type == "mssql":
            import re
            # Reemplazar TOP existente o agregar uno nuevo
            if re.search(r'\bTOP\s+\d+', query, re.IGNORECASE):
                query = re.sub(r'\bTOP\s+\d+', f'TOP {limit}', query, count=1, flags=re.IGNORECASE)
            else:
                query = query.replace("SELECT", f"SELECT TOP {limit}", 1)
        elif db_type in ("mariadb", "duckdb"):
            query = query.rstrip().rstrip(";")
            # Reemplazar LIMIT existente o agregar uno nuevo
            import re
            if re.search(r'\bLIMIT\s+\d+', query, re.IGNORECASE):
                query = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {limit}', query, count=1, flags=re.IGNORECASE)
            else:
                query = f"{query} LIMIT {limit}"

    df = pd.read_sql(query, conn)
    conn.close()
    label = _source_label(source)
    print(f"  Extraídos {len(df):,} registros de {label}")
    return df


def _fetch_csv(path, limit=None):
    df = pd.read_csv(path, nrows=limit)
    print(f"  Extraídos {len(df):,} registros de {path}")
    return df


def _fetch_json(path, limit=None):
    df = pd.read_json(path)
    if limit:
        df = df.head(limit)
    print(f"  Extraídos {len(df):,} registros de {path}")
    return df


def _source_label(source):
    stype = source["type"]
    if stype in ("csv", "json"):
        return f"{stype}://{source['path']}"
    elif stype == "duckdb":
        return f"duckdb://{source.get('path', ':memory:')}"
    else:
        return f"{stype}://{source['server']}/{source['database']}"


def test_source_connection(source):
    """Prueba la conexión a una fuente de datos."""
    source_type = source["type"]
    label = _source_label(source)

    if source_type in ("csv", "json"):
        import os
        exists = os.path.isfile(source["path"])
        status = "OK" if exists else "FALLO (archivo no encontrado)"
        print(f"    {status} - {label}")
        return exists

    try:
        conn = get_connection(source)
        if source_type == "duckdb":
            conn.execute("SELECT 1")
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        conn.close()
        print(f"    OK - {label}")
        return True
    except Exception as e:
        print(f"    FALLO - {label} ({e})")
        return False

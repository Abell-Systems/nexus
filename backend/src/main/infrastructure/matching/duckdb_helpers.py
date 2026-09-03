import duckdb


def resolve_patent_columns(con: duckdb.DuckDBPyConnection, table_name: str, extra_column: str | None = None) -> str:
    """Dynamically resolves patent column expressions based on table schema.

    Supports both canonical schemas with publication_id and snapshot schemas with publication_number.
    """
    cols = {c[0] for c in con.execute(f"DESCRIBE {table_name}").fetchall()}
    pub_col = "publication_id" if "publication_id" in cols else "publication_number"
    country_col = "country_code" if "country_code" in cols else "'ES'"
    doc_num_col = "doc_number" if "doc_number" in cols else "''"
    kind_col = "kind_code" if "kind_code" in cols else "''"
    extra_expr = f", {extra_column}" if extra_column and extra_column in cols else (f", '' AS {extra_column}" if extra_column else "")

    return f"""
        SELECT 
            {pub_col} AS publication_id,
            {country_col} AS country_code,
            {doc_num_col} AS doc_number,
            {kind_col} AS kind_code,
            title,
            abstract,
            publication_date
            {extra_expr}
        FROM {table_name}
    """

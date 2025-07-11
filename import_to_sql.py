import os
import sqlite3
import pandas as pd
import sys
import json
import datetime

def infer_sqlite_type(dtype):
    if pd.api.types.is_integer_dtype(dtype):
        return 'INTEGER'
    elif pd.api.types.is_float_dtype(dtype):
        return 'REAL'
    elif pd.api.types.is_bool_dtype(dtype):
        return 'BOOLEAN'
    else:
        return 'TEXT'

def get_logger(log_path):
    def log(msg):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(log_path, 'a') as f:
            f.write(line + '\n')
    return log

def create_indexes(cursor, table_name, columns, log):
    # Common index columns
    index_cols = ['timestamp', 'component_id', 'trace_id', 'span_id']
    for col in index_cols:
        if col in columns:
            idx_name = f'idx_{table_name}_{col}'
            try:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON "{table_name}" ("{col}")')
                log(f"Created index {idx_name} on {table_name}({col})")
            except Exception as e:
                log(f"ERROR creating index {idx_name} on {table_name}: {e}")

def import_to_sql_and_get_schema(dataset_name):
    dataset_dir = os.path.join(os.path.dirname(__file__), dataset_name)
    telemetry_dir = os.path.join(dataset_dir, 'telemetry')
    db_path = os.path.join(dataset_dir, 'data.db')
    record_csv = os.path.join(dataset_dir, 'record.csv')
    query_csv = os.path.join(dataset_dir, 'query.csv')
    schema_json = os.path.join(dataset_dir, 'schema.json')
    log_path = os.path.join(dataset_dir, 'import.log')
    log = get_logger(log_path)

    log(f"--- Starting import for dataset: {dataset_name} ---")
    # Check for schema cache
    csv_mtimes = []
    for root, dirs, files in os.walk(dataset_dir):
        for f in files:
            if f.endswith('.csv'):
                csv_mtimes.append(os.path.getmtime(os.path.join(root, f)))
    db_mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else 0
    schema_mtime = os.path.getmtime(schema_json) if os.path.exists(schema_json) else 0
    if os.path.exists(schema_json) and os.path.exists(db_path) and csv_mtimes and db_mtime >= max(csv_mtimes) and schema_mtime >= db_mtime:
        log(f"Loaded schema from cache: {schema_json}")
        with open(schema_json, 'r') as f:
            schema_summary = json.load(f)
        log(f"--- Import complete (from cache) for dataset: {dataset_name} ---")
        return schema_summary

    def import_csv_to_table(cursor, conn, csv_path, table_name):
        try:
            df = pd.read_csv(csv_path)
            columns = []
            for col in df.columns:
                coltype = infer_sqlite_type(df[col].dtype)
                columns.append(f'"{col}" {coltype}')
            schema = ', '.join(columns)
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}";')
            cursor.execute(f'CREATE TABLE "{table_name}" ({schema});')
            # Batch insert for large tables
            chunksize = 10000 if len(df) > 10000 else None
            df.to_sql(table_name, conn, if_exists='replace', index=False, chunksize=chunksize, method=None)
            log(f"Imported table: {table_name} from {csv_path} ({len(df)} rows, chunksize={chunksize})")
            create_indexes(cursor, table_name, df.columns, log)
            return df
        except Exception as e:
            log(f"ERROR importing {csv_path} to {table_name}: {e}")
            raise

    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    schema_summary = {}

    # Import record.csv and query.csv
    df_record = import_csv_to_table(cursor, conn, record_csv, 'record')
    df_query = import_csv_to_table(cursor, conn, query_csv, 'query')
    schema_summary['record'] = list(df_record.dtypes.items())
    schema_summary['query'] = list(df_query.dtypes.items())

    # Scan all telemetry files
    for date_dir in sorted(os.listdir(telemetry_dir)):
        date_path = os.path.join(telemetry_dir, date_dir)
        if not os.path.isdir(date_path):
            continue
        metric_dir = os.path.join(date_path, 'metric')
        trace_dir = os.path.join(date_path, 'trace')
        # Import all metric files
        if os.path.isdir(metric_dir):
            for metric_file in os.listdir(metric_dir):
                if not metric_file.endswith('.csv'):
                    continue
                metric_type = metric_file.replace('.csv', '')
                table_name = metric_type
                csv_path = os.path.join(metric_dir, metric_file)
                if not cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';").fetchone():
                    df = import_csv_to_table(cursor, conn, csv_path, table_name)
                    schema_summary[table_name] = list(df.dtypes.items())
                else:
                    df = pd.read_csv(csv_path)
                    chunksize = 10000 if len(df) > 10000 else None
                    df.to_sql(table_name, conn, if_exists='append', index=False, chunksize=chunksize, method=None)
                    log(f"Appended to table: {table_name} from {csv_path} ({len(df)} rows, chunksize={chunksize})")
        # Import all trace files
        if os.path.isdir(trace_dir):
            for trace_file in os.listdir(trace_dir):
                if not trace_file.endswith('.csv'):
                    continue
                trace_type = trace_file.replace('.csv', '')
                table_name = trace_type
                csv_path = os.path.join(trace_dir, trace_file)
                if not cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';").fetchone():
                    df = import_csv_to_table(cursor, conn, csv_path, table_name)
                    schema_summary[table_name] = list(df.dtypes.items())
                else:
                    df = pd.read_csv(csv_path)
                    chunksize = 10000 if len(df) > 10000 else None
                    df.to_sql(table_name, conn, if_exists='append', index=False, chunksize=chunksize, method=None)
                    log(f"Appended to table: {table_name} from {csv_path} ({len(df)} rows, chunksize={chunksize})")
    conn.commit()
    conn.close()

    # Save schema cache
    with open(schema_json, 'w') as f:
        json.dump(schema_summary, f, indent=2)
    log(f"Schema cached to {schema_json}")

    # Schema validation
    expected_tables = {'record', 'query'}
    metric_tables = [t for t in schema_summary if t.startswith('metric_')]
    trace_tables = [t for t in schema_summary if t.startswith('trace')]
    missing = []
    for t in expected_tables:
        if t not in schema_summary:
            missing.append(t)
    if not metric_tables:
        missing.append('at least one metric_* table')
    if not trace_tables:
        missing.append('at least one trace* table')
    if missing:
        log(f"WARNING: Missing tables: {', '.join(missing)}")
    log(f"--- Import complete for dataset: {dataset_name} ---")
    return schema_summary

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_to_sql.py <DATASET_NAME>")
        sys.exit(1)
    dataset_name = sys.argv[1]
    schema = import_to_sql_and_get_schema(dataset_name)
    print(f'\n--- Schema Summary for {dataset_name} ---')
    for table, cols in schema.items():
        print(f'Table: {table}')
        for col, dtype in cols:
            print(f'  {col}: {dtype}')
        print() 
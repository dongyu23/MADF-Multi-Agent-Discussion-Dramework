import os
import libsql_client
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings
import logging
import json
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PostgresClient:
    def __init__(self, dsn):
        self.dsn = dsn

    def execute(self, sql, args=None):
        conn = psycopg2.connect(self.dsn)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Replace SQLite placeholder ? with %s
                sql = sql.replace('?', '%s')
                cur.execute(sql, args)
                conn.commit()
                
                # Try to fetch results if it's a SELECT
                try:
                    rows = cur.fetchall()
                    if cur.description:
                        columns = [desc[0] for desc in cur.description]
                        return PostgresResult(rows, columns)
                except psycopg2.ProgrammingError:
                    # No results to fetch
                    pass
                
                # Check for RETURNING id (simulating lastrowid)
                # But we need to know if the query had RETURNING...
                # Actually, for INSERTs, we should modify the SQL to add RETURNING id if needed?
                # Or rely on explicit RETURNING in SQL?
                # The existing code uses lastrowid.
                # In PG, we must use RETURNING id.
                # But we can't auto-inject it easily without parsing.
                # Let's handle lastrowid by checking if 'id' is in returned rows if user added RETURNING.
                
                return PostgresResult([], [])
        finally:
            conn.close()

    def transaction(self):
        return PostgresTransaction(self.dsn)

    def close(self):
        pass

class PostgresResult:
    def __init__(self, rows, columns):
        self.rows = [tuple(row[col] for col in columns) for row in rows]
        self.columns = columns
        self.lastrowid = None # PG requires RETURNING id
        if rows and 'id' in columns:
             self.lastrowid = rows[0]['id']

class PostgresTransaction:
    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def execute(self, sql, args=None):
        sql = sql.replace('?', '%s')
        self.cursor.execute(sql, args)
        # Fetch if needed... but execute inside transaction usually doesn't return result object in libsql wrapper?
        # Wait, libsql transaction.execute returns result.
        try:
            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            res = PostgresResult(rows, columns)
            return res
        except psycopg2.ProgrammingError:
             return PostgresResult([], [])

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.cursor.close()
        self.conn.close()

class Database:
    def __init__(self):
        self.url = settings.DATABASE_URL
        self.auth_token = settings.TURSO_AUTH_TOKEN
        # Determine DB type
        self.is_postgres = self.url.startswith("postgresql://") or self.url.startswith("postgres://")
        self.is_remote = self.url.startswith("libsql://") or self.url.startswith("https://")
        
    def get_connection(self):
        if self.is_postgres:
            return PostgresClient(self.url)
            
        # ... (Existing SQLite/LibSQL logic) ...
        # Create a new client/connection for each request/scope
        # For local file, this is fast. For remote, it handles HTTP/WS.
        # sync_client is used to match the existing synchronous codebase.
        token = self.auth_token if self.is_remote else None
        
        # Ensure directory exists for local file
        if not self.is_remote and self.url.startswith("file:"):
            db_path = self.url.replace("file:", "")
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir and not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except OSError as e:
                    logger.warning(f"Failed to create database directory: {e}")

        client = libsql_client.create_client_sync(
            url=self.url,
            auth_token=token
        )
        client.execute("PRAGMA foreign_keys = ON")
        client.execute("PRAGMA journal_mode = WAL")  # Enable Write-Ahead Logging for concurrency
        client.execute("PRAGMA busy_timeout = 10000") # Increase timeout to 10s
        return client

    def init_db(self):
        """Initialize the database with schema."""
        if self.is_postgres:
            schema_file = "schema_pg.sql"
        else:
            schema_file = "schema.sql"
            
        schema_path = os.path.join(os.path.dirname(__file__), schema_file)
        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found at {schema_path}")
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # Check if DB needs init (e.g. check if users table exists)
        try:
             # Use a fresh connection
             client = self.get_connection()
             try:
                 # Check if table exists
                 try:
                     client.execute("SELECT 1 FROM users LIMIT 1")
                     logger.info("Database already initialized.")
                     return
                 except Exception:
                     # Table doesn't exist, proceed with init
                     pass
                     
                 logger.info(f"Initializing database at {self.url}...")
                 
                 # Simple split by statement separator
                 statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
                 
                 if statements:
                     # For SQLite, batch might not be supported or behaves differently in some clients
                     # Execute one by one
                     for stmt in statements:
                         try:
                             client.execute(stmt)
                         except Exception as e:
                             logger.warning(f"Error executing statement: {e}")
                             
                 logger.info("Database initialized successfully.")
             finally:
                 client.close()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise e

db_manager = Database()

@contextmanager
def db_transaction(db):
    tx = db.transaction()
    try:
        yield tx
        tx.commit()
    except Exception:
        try:
            tx.rollback()
        except Exception:
            pass
        raise
    finally:
        tx.close()

def get_db():
    """Dependency that yields a database client."""
    client = db_manager.get_connection()
    try:
        yield client
    finally:
        client.close()

class RowObject:
    """A helper class to allow attribute access to dict keys."""
    def __init__(self, data):
        self.__dict__.update(data)
    
    def __getitem__(self, item):
        return self.__dict__[item]
        
    def get(self, item, default=None):
        return self.__dict__.get(item, default)

def to_dict(row, columns):
    """Convert a Row to a dict using column names and parse JSON fields."""
    d = dict(zip(columns, row))
    # Known JSON fields
    json_fields = ['theories', 'summary_history', 'thoughts_history', 'participant_ids']
    for field in json_fields:
        if field in d and isinstance(d[field], str):
            try:
                # Try to parse if it looks like JSON
                val = d[field].strip()
                if (val.startswith('[') and val.endswith(']')) or (val.startswith('{') and val.endswith('}')):
                    d[field] = json.loads(val)
            except:
                pass
    return d

def fetch_one(result, model_class=None):
    """Return the first row as a dict or model object, or None."""
    if not result.rows:
        return None
    data = to_dict(result.rows[0], result.columns)
    if model_class:
        return model_class(**data)
    return RowObject(data)

def fetch_all(result, model_class=None):
    """Return all rows as a list of dicts or model objects."""
    if not result.rows:
        return []
    data_list = [to_dict(row, result.columns) for row in result.rows]
    if model_class:
        return [model_class(**data) for data in data_list]
    return [RowObject(data) for data in data_list]

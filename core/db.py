import pymysql
import pymysql.cursors
from flask import current_app, g


def get_conn():
    if "db_conn" not in g:
        g.db_conn = pymysql.connect(
            host=current_app.config["MYSQL_HOST"],
            port=current_app.config["MYSQL_PORT"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DB"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    return g.db_conn


def close_conn(_exc=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


def query(sql, params=None, fetchone=False):
    """Run a SELECT. Callers are responsible for including a tenant_id
    filter in `sql` whenever the table is tenant-scoped."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone() if fetchone else cur.fetchall()


def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE. Returns lastrowid for inserts."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.lastrowid


def init_app(app):
    app.teardown_appcontext(close_conn)

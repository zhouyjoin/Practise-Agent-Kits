import pymysql
import re

config = {
    'host': 'ip地址',
    'port': 3306,
    'user': '用户名',
    'password': '登陆密码',
    'db': '选择要提取的微博数据库名',
    'charset': 'utf8mb4'
}

from typing import List, Dict, Optional


def get_root_connection():
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        charset=config["charset"],
    )


def latest_weibo_database() -> str:
    conn = get_root_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT schema_name FROM information_schema.schemata")
        names = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
    candidates = []
    for n in names:
        m = re.match(r"^weibo_(\d{4})_(\d{2})_(\d{2})$", n)
        if m:
            y, mm, dd = map(int, m.groups())
            candidates.append(((y, mm, dd), n))
    if not candidates:
        raise ValueError("no weibo_YYYY_MM_DD databases available")
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def ensure_current_db() -> str:
    try:
        db = latest_weibo_database()
        config["db"] = db
        return db
    except Exception:
        return config["db"]


def get_connection():
    ensure_current_db()
    return pymysql.connect(**config)


def get_connection_for_db(db_name: str):
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        db=db_name,
        charset=config["charset"],
    )

#返回该数据库中的所有表名
def list_tables() -> List[str]:
    """
    返回数据库中的所有表名
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # 查询系统库 information_schema.tables，获取当前数据库(schema)下的所有表名
        # 使用参数化绑定传入 schema 名，避免字符串拼接造成的 SQL 注入
        # ORDER BY table_name 让返回的表名按字母顺序稳定排序，便于后续遍历
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema=%s
            ORDER BY table_name
            """,
            (config["db"],),
        )
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()



def fetch_hot_weibo(limit: int = 50, table: Optional[str] = None) -> List[Dict]:
    try:
        real_table = resolve_table(table) if table else latest_weibo_table()
    except Exception:
        real_table = latest_weibo_table()
    conn = get_connection()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cur.execute(f"SELECT title, content, comment FROM `{real_table}` LIMIT %s", (limit,))
        except Exception:
            cur.execute(f"SELECT * FROM `{real_table}` LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        conn.close()


#根据表名返回该表的所有字段信息
def describe_table(table: str) -> List[Dict]:
    conn = get_connection()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            """
            SELECT COLUMN_NAME AS name,
                   COLUMN_TYPE AS type,
                   IS_NULLABLE AS is_nullable,
                   COLUMN_DEFAULT AS default_value,
                   COLUMN_KEY AS key_type,
                   EXTRA AS extra,
                   COLUMN_COMMENT AS comment
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s
            ORDER BY ORDINAL_POSITION
            """,
            (config["db"], table),
        )
        return cur.fetchall()
    finally:
        conn.close()


#判断表是否存在
def table_exists(table: str) -> bool:
    """
    justice whether the table exists in the database,if exist return True,else return False
    """
    return table in list_tables()


def resolve_table(table: str) -> str:
    """
    resolve the table name to the real table name in the database
    if the table name is not found, raise ValueError
    """
    tables = list_tables()
    if table in tables:
        return table
    candidates = [t for t in tables if t.startswith(table)]
    if candidates:
        return candidates[0]
    raise ValueError(f"table not found: {table}")


def latest_weibo_table() -> str:
    """
    return the latest weibo table name in the database
    if no weibo_* tables available, raise ValueError
    """
    tables = list_tables()
    candidates = [t for t in tables if t.startswith("weibo_")]
    if not candidates:
        raise ValueError("no weibo_* tables available")
    return sorted(candidates)[-1]


def fetch_recent(table: str, limit: int = 50) -> List[Dict]:
    real_table = resolve_table(table)
    conn = get_connection()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cols = [c["name"] for c in describe_table(real_table)]
        #按照创建时间来排序，获取最新的limit条数据
        if "created_at" in cols:
            cur.execute(f"SELECT * FROM `{real_table}` ORDER BY `created_at` DESC LIMIT %s", (limit,))
        else:
            cur.execute(f"SELECT * FROM `{real_table}` LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        conn.close()


def fetch_top_by_metric(table: str, metric: str, limit: int = 20, desc: bool = True) -> List[Dict]:
    real_table = resolve_table(table)
    conn = get_connection()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cols = [c["name"] for c in describe_table(real_table)]
        if metric in cols:
            order = "DESC" if desc else "ASC"
            cur.execute(f"SELECT * FROM `{real_table}` ORDER BY `{metric}` {order} LIMIT %s", (limit,))
        else:
            cur.execute(f"SELECT * FROM `{real_table}` LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        conn.close()


def search_rows_keyword(table: str, keyword: str, limit: int = 20) -> List[Dict]:
    real_table = resolve_table(table)
    data = fetch_recent(real_table, limit=200)
    kw = (keyword or "").strip()
    if not kw:
        return []
    keys = ["title", "content", "comment", "text", "topics", "screen_name"]
    results: List[Dict] = []
    for item in data:
        for k in keys:
            v = str(item.get(k, ""))
            if kw in v:
                results.append(item)
                break
        if len(results) >= limit:
            break
    return results

def ensure_reports_table(target_db: Optional[str] = None):
    conn = get_connection_for_db(target_db) if target_db else get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `reports` (
              `id` INT AUTO_INCREMENT PRIMARY KEY,
              `task` VARCHAR(255),
              `content` LONGTEXT,
              `file_path` VARCHAR(1024),
              `created_at` DATETIME
            ) CHARACTER SET utf8mb4
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_report_to_db(task: str, content: str, file_path: str, target_db: Optional[str] = None) -> int:
    ensure_reports_table(target_db)
    conn = get_connection_for_db(target_db) if target_db else get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO `reports` (`task`, `content`, `file_path`, `created_at`) VALUES (%s, %s, %s, NOW())",
            (task, content, file_path),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

# 预览数据库中的所有表名
def preview_tables_and_rows():
    """
    预览数据库中的所有表名和前 
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema=%s
            ORDER BY table_name
            """,
            (config["db"],),
        )
        tables = [row[0] for row in cur.fetchall()]
        print(f"该数据库共有 {len(tables)} 张表：")
        for t in tables:
            print(t)
    except Exception as e:
        print(f"查询失败：{e}")
    finally:
        conn.close()

if __name__ == "__main__": 
    preview_tables_and_rows()
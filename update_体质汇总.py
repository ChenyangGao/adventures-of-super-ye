# /usr/bin/env python
# encoding: utf-8

import sqlite3

conn = sqlite3.connect("体质.db")
cursor = conn.cursor()

# 1. 查找所有源普通表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
source_tables = [t for t in tables if not t.startswith(('❶', '❷')) and t.endswith('体')]

# 2. 把数据插入体质汇总
cursor.execute('DELETE FROM "❷体质汇总"')
for table_name in source_tables:
    cursor.execute(f"""CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_name ON {table_name} (name)""")
    sql = f"""
        INSERT INTO "❷体质汇总" ("id", "name", "type")
        SELECT "id", REPLACE("name", ?, ''), ?
        FROM "{table_name}"
    """
    cursor.execute(sql, (table_name, table_name))

# 3. 为每张表动态创建 triggers
for table in source_tables:
    # --- BEFORE INSERT ---
    cursor.executescript(f"""\
DROP TRIGGER IF EXISTS "trg_{table}_before_insert";
CREATE TRIGGER "trg_{table}_before_insert"
BEFORE INSERT ON "{table}"
FOR EACH ROW
BEGIN
    SELECT CASE 
        WHEN NEW.name NOT LIKE '%' || '{table}' THEN 
            RAISE(ABORT, '插入失败：name 后缀必须是 "{table}"')
        WHEN LENGTH(REPLACE(NEW.name, '{table}', '')) < 2 THEN 
            RAISE(ABORT, '插入失败：name 除去 "{table}" 后缀后，长度不能小于 2')
    END;
END;

DROP TRIGGER IF EXISTS "trg_{table}_after_insert";
CREATE TRIGGER "trg_{table}_after_insert"
AFTER INSERT ON "{table}"
FOR EACH ROW
BEGIN
    INSERT INTO "❷体质汇总" ("id", "name", "type")
    VALUES (NEW.id, REPLACE(NEW.name, '{table}', ''), '{table}');
END;

DROP TRIGGER IF EXISTS "trg_{table}_before_update";
CREATE TRIGGER "trg_{table}_before_update"
BEFORE UPDATE ON "{table}"
FOR EACH ROW
BEGIN
    SELECT CASE 
        WHEN NEW.name NOT LIKE '%' || '{table}' THEN 
            RAISE(ABORT, '更新失败：name 后缀必须是 "{table}"')
        WHEN LENGTH(REPLACE(NEW.name, '{table}', '')) < 2 THEN 
            RAISE(ABORT, 'name 除去 "{table}" 后缀后，长度不能小于 2')
    END;
END;

DROP TRIGGER IF EXISTS "trg_{table}_after_update";
CREATE TRIGGER "trg_{table}_after_update"
AFTER UPDATE ON "{table}"
FOR EACH ROW
BEGIN
    INSERT INTO "❷体质汇总" ("id", "name", "type")
    SELECT NEW.id, REPLACE(NEW.name, '{table}', ''), '{table}'
    WHERE NOT EXISTS (
        SELECT 1 FROM "❷体质汇总" WHERE "id" = OLD.id AND "type" = '{table}'
    );

    UPDATE "❷体质汇总"
    SET "id" = NEW.id, 
        "name" = REPLACE(NEW.name, '{table}', ''),
        "type" = '{table}'
    WHERE "id" = OLD.id AND "type" = '{table}';
END;

DROP TRIGGER IF EXISTS "trg_{table}_after_delete";
CREATE TRIGGER "trg_{table}_after_delete"
AFTER DELETE ON "{table}"
FOR EACH ROW
BEGIN
    DELETE FROM "❷体质汇总"
    WHERE "id" = OLD.id AND "type" = '{table}';
END;""")

conn.commit()
conn.close()

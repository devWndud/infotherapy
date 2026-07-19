#!/bin/bash

set -e

NAME_TO_DELETE="${1:-김태호}"

python - <<PY
import sqlite3
import os

name_to_delete = os.environ.get("NAME_TO_DELETE", "김태호")
conn = sqlite3.connect("infotherapy.db")
cur = conn.cursor()

row = cur.execute("SELECT id, name, student_id FROM users WHERE name = ?", (name_to_delete,)).fetchone()

if row:
    cur.execute("DELETE FROM users WHERE name = ?", (name_to_delete,))
    conn.commit()
    print(f"삭제 완료: {row}")
else:
    print("해당 이름의 사용자가 없습니다.")

conn.close()
PY
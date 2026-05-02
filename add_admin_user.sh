#!/usr/bin/env bash
set -euo pipefail

if [ "${#}" -lt 2 ]; then
  echo "Usage: $0 <username> <password> [env_file]"
  echo "Example: $0 admin rayuela backend/.env"
  exit 1
fi

USERNAME="$1"
PASSWORD="$2"
ENV_FILE="${3:-backend/.env}"

python3 - "$USERNAME" "$PASSWORD" "$ENV_FILE" <<'PY'
import hashlib
import json
import os
import re
import secrets
import sys

username, password, env_file = sys.argv[1], sys.argv[2], sys.argv[3]
if not os.path.exists(env_file):
    open(env_file, "a").close()

with open(env_file, "r", encoding="utf-8") as f:
    content = f.read()

m = re.search(r"^ADMIN_USERS_JSON=(.*)$", content, flags=re.MULTILINE)
users = {}
if m:
    raw = m.group(1).strip()
    try:
        users = json.loads(raw)
    except Exception:
        users = {}

salt = secrets.token_hex(16)
it = 200000
dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), it).hex()
users[username] = f"pbkdf2_sha256${it}${salt}${dk}"

line = "ADMIN_USERS_JSON=" + json.dumps(users, separators=(",", ":"))
if m:
    content = re.sub(r"^ADMIN_USERS_JSON=.*$", line, content, flags=re.MULTILINE)
else:
    if content and not content.endswith("\n"):
        content += "\n"
    content += line + "\n"

with open(env_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ Added/updated admin user '{username}' in {env_file}")
PY

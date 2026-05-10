import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Dict

from dotenv import dotenv_values
from fastapi import Header, HTTPException

from config import settings

# .env lives one level above this file (backend/.env)
_ENV_FILE = Path(__file__).parent.parent / ".env"


def _users() -> Dict[str, str]:
    # Re-read .env on every call so new users take effect without restarting.
    env = dotenv_values(_ENV_FILE) if _ENV_FILE.exists() else {}
    raw_json = env.get("ADMIN_USERS_JSON") or settings.admin_users_json
    try:
        raw = json.loads(raw_json)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _verify_password(password: str, encoded: str) -> bool:
    # format: pbkdf2_sha256$iter$salt_hex$hash_hex
    try:
        algo, it_s, salt_hex, hash_hex = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        it = int(it_s)
        calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), it)
        return hmac.compare_digest(calc.hex(), hash_hex)
    except Exception:
        return False


def authenticate_admin(username: str, password: str) -> bool:
    user_map = _users()
    encoded = user_map.get(username)
    if not encoded:
        return False
    return _verify_password(password, encoded)


def issue_token(username: str) -> str:
    payload = {"u": username, "exp": int(time.time()) + settings.admin_token_ttl_seconds}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    sig = hmac.new(settings.admin_auth_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token: str) -> dict:
    try:
        body, sig = token.rsplit(".", 1)
        expected = hmac.new(
            settings.admin_auth_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad-signature")
        payload = json.loads(base64.urlsafe_b64decode(body.encode("utf-8")).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid admin token")


def require_admin_auth(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing admin authorization")
    token = authorization.split(" ", 1)[1]
    return verify_token(token)

"""
auth.py
-------
Login and user-account management (admin can create/disable cashiers).
"""

import hmac
import re
from datetime import datetime, timedelta
from database import get_connection, hash_password

MIN_PASSWORD_LENGTH = 4
MAX_RECOVERY_ATTEMPTS = 5          # wrong answers allowed before a temporary lockout
RECOVERY_LOCKOUT_MINUTES = 5

SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What is your mother's maiden name?",
    "What city or town were you born in?",
    "What was the name of your elementary school?",
    "What was your childhood nickname?",
    "What is the name of your favorite teacher?",
]

NO_RECOVERY_MESSAGE = (
    "Password recovery isn't set up for this account.\n"
    "Please ask an administrator to reset your password (Users \u2192 Reset Password)."
)


def verify_login(username: str, password: str):
    """Returns the user row (as dict) if credentials are valid and active, else None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND active = 1", (username.strip(),)
    ).fetchone()
    conn.close()
    if row and row["password_hash"] == hash_password(password):
        return dict(row)
    return None


def get_user(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY role, username").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username, password, full_name, role):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (username.strip(), hash_password(password), full_name.strip(), role, datetime.now().isoformat()),
        )
        conn.commit()
        return True, "User created successfully."
    except Exception as e:
        return False, f"Could not create user: {e}"
    finally:
        conn.close()


def set_user_active(user_id, active: bool):
    conn = get_connection()
    conn.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))
    conn.commit()
    conn.close()


def reset_password(user_id, new_password):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET password_hash=?, recovery_failed_attempts=0, recovery_locked_until=NULL WHERE id=?",
        (hash_password(new_password), user_id),
    )
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# "Forgot password" support (security question + answer)
# ----------------------------------------------------------------------
def _normalize_answer(answer: str) -> str:
    """Case/whitespace-insensitive so 'Fluffy ' and 'fluffy' match."""
    return re.sub(r"\s+", " ", (answer or "").strip().lower())


def _hash_answer(answer: str) -> str:
    return hash_password("recovery:" + _normalize_answer(answer))


def has_recovery(user: dict) -> bool:
    return bool(user.get("security_question") and user.get("security_answer_hash"))


def set_recovery(user_id, question: str, answer: str):
    """Saves (or replaces) the security question/answer for a user. Returns (ok, message)."""
    question = (question or "").strip()
    if not question:
        return False, "Please choose or type a security question."
    if len(_normalize_answer(answer)) < 2:
        return False, "Please enter an answer (at least 2 characters)."

    conn = get_connection()
    conn.execute(
        "UPDATE users SET security_question=?, security_answer_hash=?, "
        "recovery_failed_attempts=0, recovery_locked_until=NULL WHERE id=?",
        (question, _hash_answer(answer), user_id),
    )
    conn.commit()
    conn.close()
    return True, "Recovery question saved."


def _get_recovery_row(username: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND active = 1", ((username or "").strip(),)
    ).fetchone()
    conn.close()
    if row is None or not (row["security_question"] and row["security_answer_hash"]):
        return None
    return row


def _lockout_message(row):
    """Returns a message if the account is currently locked out of recovery, else None."""
    until = row["recovery_locked_until"]
    if not until:
        return None
    try:
        remaining = datetime.fromisoformat(until) - datetime.now()
    except ValueError:
        return None
    if remaining.total_seconds() <= 0:
        return None
    minutes = max(1, int(remaining.total_seconds() // 60) + 1)
    return f"Too many incorrect answers. Please try again in about {minutes} minute(s)."


def get_recovery_question(username: str):
    """
    Step 1 of 'Forgot password'. Returns (question, error_message); exactly one is None.
    Unknown users, disabled users and users without a question all get the same
    message, so the screen can't be used to discover which usernames exist.
    """
    row = _get_recovery_row(username)
    if row is None:
        return None, NO_RECOVERY_MESSAGE
    locked = _lockout_message(row)
    if locked:
        return None, locked
    return row["security_question"], None


def reset_password_with_answer(username: str, answer: str, new_password: str):
    """Step 2: checks the answer and, if correct, sets the new password. Returns (ok, message)."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"Password should be at least {MIN_PASSWORD_LENGTH} characters."

    row = _get_recovery_row(username)
    if row is None:
        return False, NO_RECOVERY_MESSAGE
    locked = _lockout_message(row)
    if locked:
        return False, locked

    conn = get_connection()
    try:
        if hmac.compare_digest(row["security_answer_hash"], _hash_answer(answer)):
            conn.execute(
                "UPDATE users SET password_hash=?, recovery_failed_attempts=0, recovery_locked_until=NULL WHERE id=?",
                (hash_password(new_password), row["id"]),
            )
            conn.commit()
            return True, "Password updated. You can now sign in."

        attempts = (row["recovery_failed_attempts"] or 0) + 1
        if attempts >= MAX_RECOVERY_ATTEMPTS:
            until = (datetime.now() + timedelta(minutes=RECOVERY_LOCKOUT_MINUTES)).isoformat()
            conn.execute(
                "UPDATE users SET recovery_failed_attempts=0, recovery_locked_until=? WHERE id=?",
                (until, row["id"]),
            )
            conn.commit()
            return False, (f"Too many incorrect answers. Password recovery is locked for "
                           f"{RECOVERY_LOCKOUT_MINUTES} minutes.")
        conn.execute("UPDATE users SET recovery_failed_attempts=? WHERE id=?", (attempts, row["id"]))
        conn.commit()
        left = MAX_RECOVERY_ATTEMPTS - attempts
        return False, f"That answer doesn't match. {left} attempt(s) left."
    finally:
        conn.close()

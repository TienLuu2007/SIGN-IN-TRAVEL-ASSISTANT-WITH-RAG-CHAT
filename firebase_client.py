import os
import requests
from dotenv import load_dotenv

BASE_URL = "https://identitytoolkit.googleapis.com/v1/accounts"


def _get_api_key() -> str:
    """Reloads .env and returns a clean Firebase Web API Key."""
    load_dotenv(override=True)
    return os.getenv("FIREBASE_API_KEY", "").strip().strip('"').strip("'")


def _parse_firebase_error(response_json: dict) -> str:
    """Translates Firebase REST API error codes into clear user-facing messages."""
    error_msg = response_json.get("error", {}).get("message", "UNKNOWN_ERROR")
    if (
        "INVALID_LOGIN_CREDENTIALS" in error_msg
        or "INVALID_PASSWORD" in error_msg
        or "EMAIL_NOT_FOUND" in error_msg
    ):
        return "Wrong email or password. Please try again."
    if "EMAIL_EXISTS" in error_msg:
        return "This email is already registered. Please sign in instead."
    if "WEAK_PASSWORD" in error_msg:
        return "Password should be at least 6 characters long."
    if "INVALID_EMAIL" in error_msg:
        return "Please enter a valid email address."
    if "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
        return "Too many failed attempts. Please wait a moment and try again."
    if "USER_DISABLED" in error_msg:
        return "This user account has been disabled."
    if "API_KEY_INVALID" in error_msg:
        return "Invalid FIREBASE_API_KEY in .env file. Please check your Firebase project settings."
    return f"Authentication error: {error_msg}"


def sign_in(email: str, password: str) -> tuple[bool, dict | str]:
    """Signs in an existing user with email and password via Firebase Auth REST API."""
    api_key = _get_api_key()
    if not api_key:
        return False, "Missing FIREBASE_API_KEY in .env file."
    if not email or not email.strip() or not password:
        return False, "Please enter both email and password."

    url = f"{BASE_URL}:signInWithPassword?key={api_key}"
    payload = {
        "email": email.strip(),
        "password": password,
        "returnSecureToken": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            return True, data  # Contains 'idToken', 'email', 'localId'
        return False, _parse_firebase_error(data)
    except requests.exceptions.RequestException:
        return False, "Network error: Could not reach Firebase Authentication server."


def sign_up(email: str, password: str) -> tuple[bool, dict | str]:
    """Creates a new user account with email and password via Firebase Auth REST API."""
    api_key = _get_api_key()
    if not api_key:
        return False, "Missing FIREBASE_API_KEY in .env file."
    if not email or not email.strip() or not password:
        return False, "Please enter both email and password."

    url = f"{BASE_URL}:signUp?key={api_key}"
    payload = {
        "email": email.strip(),
        "password": password,
        "returnSecureToken": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            return True, data  # Contains 'idToken', 'email', 'localId'
        return False, _parse_firebase_error(data)
    except requests.exceptions.RequestException:
        return False, "Network error: Could not reach Firebase Authentication server."

import os
import json
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "users.json")

app = Flask(__name__)
CORS(app)  # allow cross-origin (useful for frontend / Postman from different origins)

# ----------------- Helpers & Persistence ----------------- #

def load_data():
    """Load users from JSON file; return list."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_data(users):
    """Save users list to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def next_id(users):
    """Return next auto-increment id."""
    if not users:
        return 1
    return max(u["id"] for u in users) + 1

def find_user(users, user_id):
    return next((u for u in users if u["id"] == user_id), None)

def validate_user_payload(payload, require_email=True):
    """Basic validation for incoming user data."""
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object."
    name = payload.get("name")
    email = payload.get("email")
    if not name or not isinstance(name, str) or len(name.strip()) < 2:
        return False, "Field 'name' is required (min 2 chars)."
    if require_email:
        if not email or "@" not in email or len(email.strip()) < 5:
            return False, "Field 'email' is required and must look like an email."
    return True, None

# Load at startup
users = load_data()

# If empty, create some sample users
if not users:
    users = [
        {"id": 1, "name": "Aman", "email": "aman@example.com", "created_at": str(datetime.utcnow())},
        {"id": 2, "name": "Priya", "email": "priya@example.com", "created_at": str(datetime.utcnow())}
    ]
    save_data(users)

# ----------------- Routes ----------------- #

@app.route("/")
def home():
    return jsonify({
        "message": "User Management REST API",
        "routes": {
            "GET /users": "list users (supports ?q=&page=&limit=)",
            "POST /users": "create user",
            "GET /users/<id>": "get user by id",
            "PUT /users/<id>": "update user",
            "DELETE /users/<id>": "delete user"
        }
    })

@app.route("/users", methods=["GET"])
def get_users():
    """Return list of users. Supports search (q), page, limit."""
    q = request.args.get("q", "").strip().lower()
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 0))
    except ValueError:
        return jsonify({"error": "page and limit must be integers"}), 400

    filtered = users
    if q:
        filtered = [u for u in users if q in u.get("name", "").lower() or q in u.get("email", "").lower()]

    total = len(filtered)
    if limit > 0:
        start = (page - 1) * limit
        end = start + limit
        page_data = filtered[start:end]
    else:
        page_data = filtered

    return jsonify({
        "meta": {
            "total": total,
            "page": page,
            "limit": limit or "all"
        },
        "data": page_data
    })

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = find_user(users, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)

@app.route("/users", methods=["POST"])
def create_user():
    payload = request.get_json(force=True, silent=True)
    ok, err = validate_user_payload(payload)
    if not ok:
        return jsonify({"error": err}), 400

    # prevent duplicate email
    if any(u for u in users if u.get("email", "").lower() == payload["email"].lower()):
        return jsonify({"error": "User with this email already exists."}), 409

    new_user = {
        "id": next_id(users),
        "name": payload["name"].strip(),
        "email": payload["email"].strip(),
        "created_at": str(datetime.utcnow())
    }
    users.append(new_user)
    save_data(users)
    return jsonify({"message": "User created", "user": new_user}), 201

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = find_user(users, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "No JSON payload provided"}), 400

    # allow updating name & email
    name = payload.get("name")
    email = payload.get("email")

    if name:
        if not isinstance(name, str) or len(name.strip()) < 2:
            return jsonify({"error": "Invalid name"}), 400
        user["name"] = name.strip()

    if email:
        if "@" not in email or len(email.strip()) < 5:
            return jsonify({"error": "Invalid email"}), 400
        # check duplicate email
        if any(u for u in users if u["id"] != user_id and u.get("email","").lower() == email.lower()):
            return jsonify({"error": "Another user with this email exists."}), 409
        user["email"] = email.strip()

    user["updated_at"] = str(datetime.utcnow())
    save_data(users)
    return jsonify({"message": "User updated", "user": user})

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    global users
    user = find_user(users, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    users = [u for u in users if u["id"] != user_id]
    save_data(users)
    return jsonify({"message": f"User (id={user_id}) deleted"})

# ----------------- Run ----------------- #
if __name__ == "__main__":
    # debug=True only in development
    app.run(host="127.0.0.1", port=5000, debug=True)

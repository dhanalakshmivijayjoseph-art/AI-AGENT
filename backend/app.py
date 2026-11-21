"""app.py - Flask server. Run with:  python app.py"""
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    from . import database as db
    from .ai_engine import get_ai_response, AIError
except ImportError:  # Running directly from the backend directory on Windows.
    import database as db
    from ai_engine import get_ai_response, AIError

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "..", "public")

# Vercel serves /public files from its CDN. This route serves them locally.
app = Flask(__name__, static_folder=None)
CORS(app)  # allows the page to call the API even if opened as a file
db.init_db()


@app.route("/")
def home():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/<path:filename>")
def local_public_file(filename):
    return send_from_directory(PUBLIC_DIR, filename)


def make_title(text):
    """Chat title = first 40 characters of the first question."""
    text = " ".join(text.split())
    return text[:40] + ("..." if len(text) > 40 else "")


@app.route("/api/new-chat", methods=["POST"])
def new_chat():
    return jsonify({"conversation_id": db.create_conversation()})


@app.route("/api/conversations", methods=["GET"])
def conversations():
    return jsonify(db.list_conversations())


@app.route("/api/history", methods=["GET"])
def history():
    conv_id = request.args.get("conversation_id", type=int)
    if not conv_id or not db.conversation_exists(conv_id):
        return jsonify({"error": "Conversation not found."}), 404
    return jsonify(db.get_messages(conv_id))


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    conv_id = data.get("conversation_id")
    regenerate = bool(data.get("regenerate"))

    if not regenerate and not message:
        return jsonify({"error": "Please type a message."}), 400

    # Start a new conversation if none was given
    if not conv_id or not db.conversation_exists(conv_id):
        conv_id = db.create_conversation()

    if regenerate:
        db.delete_last_assistant_message(conv_id)
    else:
        db.add_message(conv_id, "user", message)
        if len(db.get_messages(conv_id)) == 1:  # first message -> set the title
            db.rename_conversation(conv_id, make_title(message))

    stored = db.get_messages(conv_id)
    if not stored or stored[-1]["role"] != "user":
        return jsonify({"error": "Nothing to answer."}), 400
    history = [{"role": m["role"], "content": m["message"]} for m in stored]

    try:
        answer = get_ai_response(history)
    except AIError as e:
        return jsonify({"error": str(e), "conversation_id": conv_id}), 502
    except Exception as e:  # unexpected problem
        print("Unexpected error:", e)
        return jsonify({"error": "Something went wrong on the server."}), 500

    db.add_message(conv_id, "assistant", answer)
    return jsonify({"conversation_id": conv_id, "reply": answer})


@app.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
def delete_conv(conv_id):
    db.delete_conversation(conv_id)
    return jsonify({"ok": True})


@app.route("/api/conversations/<int:conv_id>", methods=["PATCH"])
def rename_conv(conv_id):
    title = ((request.get_json(silent=True) or {}).get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title cannot be empty."}), 400
    db.rename_conversation(conv_id, title[:80])
    return jsonify({"ok": True})


@app.route("/api/conversations/<int:conv_id>/clear", methods=["POST"])
def clear_conv(conv_id):
    db.clear_messages(conv_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)

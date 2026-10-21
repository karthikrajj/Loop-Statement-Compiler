"""
app.py
======
Flask backend for the C Loop Compiler web application.

Endpoints:
- GET  /              : Serves the web application interface (index.html)
- GET  /style.css     : Serves CSS stylesheet
- GET  /script.js     : Serves frontend JavaScript
- POST /compile       : Primary compilation endpoint
- GET  /api/status    : Returns compiler status & mode (real vs. demo)
- GET  /api/examples  : Returns list of built-in C loop examples
- GET  /api/examples/<name> : Returns code for a specific example
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from compiler_adapter import CompilerAdapter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(BASE_DIR, "examples")

app = Flask(__name__, static_folder=BASE_DIR)
adapter = CompilerAdapter()


# Metadata for the built-in examples
EXAMPLES_METADATA = [
    {
        "id": "for_loop",
        "filename": "for_loop.c",
        "title": "Valid 'for' Loop",
        "category": "valid",
        "description": "Standard for-loop calculating cumulative sum with printf.",
    },
    {
        "id": "while_loop",
        "filename": "while_loop.c",
        "title": "Valid 'while' Loop",
        "category": "valid",
        "description": "Standard while-loop with condition check and counter increment.",
    },
    {
        "id": "do_while_loop",
        "filename": "do_while_loop.c",
        "title": "Valid 'do-while' Loop",
        "category": "valid",
        "description": "Do-while loop ensuring at least one execution before condition check.",
    },
    {
        "id": "nested_loops",
        "filename": "nested_loops.c",
        "title": "Nested Loops (for + while)",
        "category": "valid",
        "description": "2D loop structure demonstrating nested loop parsing.",
    },
    {
        "id": "missing_semicolon",
        "filename": "missing_semicolon.c",
        "title": "Error: Missing Semicolon",
        "category": "error",
        "description": "Demonstrates detection of a missing semicolon in variable declaration.",
    },
    {
        "id": "mismatched_braces",
        "filename": "mismatched_braces.c",
        "title": "Error: Mismatched Braces",
        "category": "error",
        "description": "Demonstrates detection of an unclosed '{' block.",
    },
    {
        "id": "invalid_condition",
        "filename": "invalid_condition.c",
        "title": "Error: Invalid Loop Condition",
        "category": "error",
        "description": "Demonstrates detection of malformed condition syntax '(i < )'.",
    },
]


@app.route("/")
def index():
    """Serves the main single-page web interface."""
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/style.css")
def serve_css():
    """Serves CSS styles."""
    return send_from_directory(BASE_DIR, "style.css", mimetype="text/css")


@app.route("/script.js")
def serve_js():
    """Serves JavaScript application code."""
    return send_from_directory(BASE_DIR, "script.js", mimetype="application/javascript")


@app.route("/api/status", methods=["GET"])
def compiler_status():
    """
    Returns the operational mode and real compiler binary status.
    Used by frontend to render the 'Real Compiler' vs 'Demo Mode' badge.
    """
    status = adapter.get_status()
    return jsonify(status)


@app.route("/api/examples", methods=["GET"])
def list_examples():
    """Returns the list of example programs with their metadata and source code."""
    result = []
    for ex in EXAMPLES_METADATA:
        filepath = os.path.join(EXAMPLES_DIR, ex["filename"])
        code = ""
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                code = f"// Error reading example file: {str(e)}"
        result.append({
            "id": ex["id"],
            "title": ex["title"],
            "category": ex["category"],
            "description": ex["description"],
            "code": code,
        })
    return jsonify({"examples": result})


@app.route("/api/examples/<example_id>", methods=["GET"])
def get_example(example_id):
    """Returns a specific example by ID."""
    match = next((ex for ex in EXAMPLES_METADATA if ex["id"] == example_id), None)
    if not match:
        return jsonify({"error": f"Example '{example_id}' not found"}), 404

    filepath = os.path.join(EXAMPLES_DIR, match["filename"])
    if not os.path.isfile(filepath):
        return jsonify({"error": f"File '{match['filename']}' not found"}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    return jsonify({
        "id": match["id"],
        "title": match["title"],
        "category": match["category"],
        "description": match["description"],
        "code": code,
    })


@app.route("/compile", methods=["POST"])
def compile_endpoint():
    """
    Primary compilation endpoint.
    Accepts JSON: {"source_code": "..."}
    Returns structured JSON with tokens, AST, errors, warnings, and compiler mode.
    """
    source_code = None

    if request.is_json:
        data = request.get_json(silent=True) or {}
        source_code = data.get("source_code")
        if isinstance(source_code, dict):
            source_code = source_code.get("value") or source_code.get("source_code") or ""
    elif request.form:
        source_code = request.form.get("source_code")
    else:
        # Check raw data as fallback
        raw_body = request.get_data(as_text=True)
        if raw_body:
            source_code = raw_body

    if source_code is None:
        return jsonify({
            "success": False,
            "mode": "validation",
            "tokens": [],
            "ast": "",
            "errors": [
                {
                    "type": "BadRequest",
                    "message": "Missing 'source_code' field in request body.",
                    "line": 1,
                    "column": 1,
                }
            ],
            "warnings": [],
            "message": "Invalid request: missing source code",
            "execution_time_ms": 0,
        }), 400

    # Execute compilation through the adapter layer
    result = adapter.compile_source(source_code)

    # Return result with 200 (compilation errors are in the JSON body)
    return jsonify(result), 200


@app.errorhandler(404)
def handle_404(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def handle_500(e):
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"==================================================")
    print(f"  Loop Compiler Web Server starting on port {port}")
    status = adapter.get_status()
    print(f"  Compiler Mode: {status['mode'].upper()}")
    if status['real_compiler_available']:
        print(f"  Compiler Binary: {status['compiler_binary']}")
    else:
        print(f"  Demo Mode active: Build compiler/compiler.c for real binary.")
    print(f"  Open in browser: http://127.0.0.1:{port}")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)

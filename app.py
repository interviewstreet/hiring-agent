"""
Flask web server for the Hiring Agent frontend.
Provides file upload, settings management, and streams the scoring pipeline output in real-time.
"""

import os
import sys
import json
import uuid
import threading
import queue
import io
import contextlib
import tempfile
import shutil
import importlib
from pathlib import Path

from flask import Flask, request, jsonify, Response, send_from_directory, stream_with_context

app = Flask(__name__, static_folder="frontend", static_url_path="")

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "hiring_agent_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

# All supported Gemini models (from prompt.py)
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]

# Store active jobs: job_id -> {"queue": Queue, "status": str, "thread": Thread}
jobs = {}

class OutputCapture:
    """Captures both stdout and stderr into a queue for streaming."""

    def __init__(self, output_queue, original_stream, stream_name="stdout"):
        self.queue = output_queue
        self.original = original_stream
        self.stream_name = stream_name

    def write(self, text):
        if text:
            self.queue.put(text)
            try:
                self.original.write(text)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Windows console (cp1252) can't render emoji — skip it there,
                # the browser stream still gets the full text via the queue.
                pass

    def flush(self):
        self.original.flush()


def run_scoring_pipeline(pdf_path, output_queue, api_key, model_name):
    """Run the scoring pipeline in a thread, capturing all output."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    sys.stdout = OutputCapture(output_queue, old_stdout, "stdout")
    sys.stderr = OutputCapture(output_queue, old_stderr, "stderr")

    try:
        from score import main as score_main
        score = score_main(pdf_path, api_key=api_key, model_name=model_name)
        if score is None:
            output_queue.put("\n❌ Evaluation failed to produce a valid report. (Check rate limits or file quality)\n")
            output_queue.put("__STATUS__:FAILED")
        else:
            output_queue.put("\n✅ Evaluation complete.\n")
            output_queue.put("__STATUS__:SUCCESS")
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg or "400 API key" in error_msg:
            output_queue.put(f"\n❌ Error: Your Gemini API Key is invalid or expired. Please update it in Settings.\n")
        else:
            output_queue.put(f"\n❌ Error: {error_msg}\n")
        output_queue.put("__STATUS__:FAILED")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        output_queue.put(None)  # Sentinel: signals end of stream


@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


# --- Upload & Streaming ---

@app.route("/api/upload", methods=["POST"])
def upload_resume():
    """Handle resume PDF upload and start scoring."""
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted"}), 400

    # Save file
    job_id = str(uuid.uuid4())
    save_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(save_dir, exist_ok=True)
    pdf_path = os.path.join(save_dir, file.filename)
    file.save(pdf_path)

    # Get local settings from frontend
    api_key = request.form.get("api_key", "").strip()
    model_name = request.form.get("model", "gemini-2.5-flash").strip()

    if not api_key:
        return jsonify({"error": "No API key provided"}), 400

    # Create output queue
    output_queue = queue.Queue()

    # Start scoring in background thread
    thread = threading.Thread(
        target=run_scoring_pipeline,
        args=(pdf_path, output_queue, api_key, model_name),
        daemon=True,
    )
    jobs[job_id] = {
        "queue": output_queue,
        "status": "running",
        "thread": thread,
        "pdf_path": pdf_path,
    }
    thread.start()

    return jsonify({"job_id": job_id, "filename": file.filename})


@app.route("/api/stream/<job_id>")
def stream_output(job_id):
    """Stream scoring output as Server-Sent Events."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    def generate():
        q = jobs[job_id]["queue"]
        success_flag = False
        while True:
            try:
                msg = q.get(timeout=120)
                if msg is None:
                    # End sentinel
                    yield f"data: {json.dumps({'type': 'done', 'success': success_flag})}\n\n"
                    break
                
                if isinstance(msg, str) and msg.startswith('__STATUS__:'):
                    success_flag = (msg == '__STATUS__:SUCCESS')
                    continue

                yield f"data: {json.dumps({'type': 'output', 'text': msg})}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)

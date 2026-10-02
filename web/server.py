"""Web UI for the hiring agent. Serves the page and scores an uploaded PDF."""

import json
import os
import sys
import tempfile
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import github as github_mod
import score as score_mod
from roles import list_available_roles, load_role

# Don't store uploaded resumes or evaluation rows. Do reuse public GitHub cache
# so a repeat score doesn't burn the unauthenticated rate limit and stall.
score_mod.DEVELOPMENT_MODE = False
github_mod.DEVELOPMENT_MODE = True

WEB = Path(__file__).resolve().parent
MAX_BYTES = 8 * 1024 * 1024
SCORE_LOCK = threading.Lock()
ROLES = {name: load_role(name) for name in list_available_roles()}


def parse_multipart(content_type, body):
    if "multipart/form-data" not in (content_type or ""):
        raise ValueError("Upload the resume as a form.")
    boundary = None
    for piece in content_type.split(";"):
        piece = piece.strip()
        if piece.startswith("boundary="):
            boundary = piece.split("=", 1)[1].strip().strip('"')
    if not boundary:
        raise ValueError("Upload was missing a form boundary.")

    fields = {}
    files = {}
    delimiter = b"--" + boundary.encode()
    for chunk in body.split(delimiter):
        if chunk in (b"", b"--", b"--\r\n"):
            continue
        chunk = chunk.strip(b"\r\n")
        if chunk.endswith(b"--"):
            chunk = chunk[:-2].rstrip(b"\r\n")
        if b"\r\n\r\n" not in chunk:
            continue
        raw_head, data = chunk.split(b"\r\n\r\n", 1)
        if data.endswith(b"\r\n"):
            data = data[:-2]
        headers = {}
        for line in raw_head.decode("utf-8", "replace").split("\r\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.lower()] = value.strip()
        name = filename = None
        for piece in headers.get("content-disposition", "").split(";"):
            piece = piece.strip()
            if piece.startswith("name="):
                name = piece.split("=", 1)[1].strip().strip('"')
            elif piece.startswith("filename="):
                filename = piece.split("=", 1)[1].strip().strip('"')
        if not name:
            continue
        if filename is None:
            fields[name] = data.decode("utf-8", "replace")
        else:
            files[name] = {
                "filename": filename,
                "type": headers.get("content-type", ""),
                "data": data,
            }
    return fields, files


def public_error(exc):
    text = str(exc)
    if "401" in text or "Unauthorized" in text:
        return (
            "The PDF was received. Scoring never started because the model rejected "
            "the API key in .env. Put a working key there and upload again."
        )
    if "429" in text:
        return "The model is rate-limiting requests. Wait a minute and try again."
    if "Unknown model" in text or "requires" in text and "env var" in text:
        return text
    if not text:
        return "Scoring failed."
    return text if len(text) <= 500 else text[:500]


def report(evaluation, role, candidate_name):
    if not evaluation:
            raise RuntimeError(
                "Scoring stopped before a report was produced. "
                "Check the model key in .env, or upload a text-based PDF resume."
            )

    total = 0.0
    out_of = 0
    categories = []
    dumped = evaluation.scores.model_dump()
    for category in role.categories:
        data = dumped.get(category.key)
        if not data:
            continue
        capped = min(float(data["score"]), float(data["max"]))
        total += capped
        out_of += int(data["max"])
        categories.append(
            {
                "key": category.key,
                "label": category.label,
                "score": capped,
                "max": int(data["max"]),
                "evidence": data["evidence"],
            }
        )

    bonus = evaluation.bonus_points
    deductions = evaluation.deductions
    if bonus:
        total += float(bonus.total)
    if deductions:
        total -= float(deductions.total)
    ceiling = out_of + role.bonus_max
    if total > ceiling:
        total = float(ceiling)

    return {
        "candidate": candidate_name or "Candidate",
        "role": role.name,
        "position": role.position_title,
        "score": total,
        "out_of": out_of,
        "categories": categories,
        "bonus": (
            {"total": float(bonus.total), "breakdown": bonus.breakdown}
            if bonus
            else None
        ),
        "deductions": (
            {"total": float(deductions.total), "reasons": deductions.reasons}
            if deductions
            else None
        ),
        "strengths": list(evaluation.key_strengths or []),
        "gaps": list(evaluation.areas_for_improvement or []),
    }


def score_upload(data, filename, role_name):
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
    if role_name not in ROLES:
        raise ValueError("Pick a role that exists.")
    if not data:
        raise ValueError("That file is empty.")
    if not data.startswith(b"%PDF"):
        raise ValueError("Upload a PDF resume.")
    suffix = ".pdf"
    if filename and not filename.lower().endswith(".pdf"):
        raise ValueError("Upload a PDF resume.")

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.close()
        with SCORE_LOCK:
            evaluation, candidate_name = score_mod.main(tmp.name, ROLES[role_name])
        return report(evaluation, ROLES[role_name], candidate_name)
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status, body, content_type):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status, data):
        self._send(status, json.dumps(data), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        path = path.rstrip("/") or "/"
        pages = {"/": "index.html", "/example": "example.html"}
        if path in pages:
            self._send(200, (WEB / pages[path]).read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/app.css":
            self._send(200, (WEB / "app.css").read_bytes(), "text/css; charset=utf-8")
            return
        if path == "/api/roles":
            self._json(
                200,
                    {
                        "roles": [
                            {
                                "name": role.name,
                                "position": role.position_title,
                                "bonus_max": role.bonus_max,
                                "categories": [
                                    {
                                        "key": category.key,
                                        "label": category.label,
                                        "max": category.max,
                                    }
                                    for category in role.categories
                                ],
                            }
                            for role in ROLES.values()
                        ]
                    },
            )
            return
        self._json(404, {"error": "Not found."})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/score":
            self._json(404, {"error": "Not found."})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0 or length > MAX_BYTES + 64 * 1024:
            self._json(400, {"error": "Upload a PDF under 8 MB."})
            return
        body = self.rfile.read(length)
        try:
            fields, files = parse_multipart(self.headers.get("Content-Type", ""), body)
            upload = files.get("resume")
            if not upload:
                raise ValueError("Choose a PDF resume.")
            if len(upload["data"]) > MAX_BYTES:
                raise ValueError("Upload a PDF under 8 MB.")
            role_name = fields.get("role") or next(iter(ROLES))
            result = score_upload(upload["data"], upload["filename"], role_name)
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return
        except RuntimeError as exc:
            self._json(502, {"error": str(exc)})
            return
        except Exception as exc:
            traceback.print_exc()
            self._json(502, {"error": public_error(exc)})
            return
        self._json(200, result)


def main():
    if not ROLES:
        sys.exit("No roles found under roles/.")
    port = int(os.environ.get("PORT", "8787"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Hiring agent UI at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

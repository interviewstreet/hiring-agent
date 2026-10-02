import dataclasses
import http.server
import json
import threading
from typing import Dict, Optional

import pytest
import requests

import models

RETRY_INFO_TYPE = "type.googleapis.com/google.rpc.RetryInfo"
LONG_RETRY_DELAY = "10330s"


def make_response(
    status_code: int = 200,
    body: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.reason = "Test Reason"
    response.url = "https://example.test/chat/completions"
    response._content = body if body is not None else b""
    response.headers.update(headers or {})
    return response


def make_error_body(message: str, retry_delay: Optional[str] = None) -> Dict:
    error = {"message": message, "details": []}
    if retry_delay is not None:
        error["details"].append({"@type": RETRY_INFO_TYPE, "retryDelay": retry_delay})
    return {"error": error}


@dataclasses.dataclass(frozen=True)
class Scenario:
    response: requests.Response
    expected_delay: Optional[float]


@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            Scenario(
                response=make_response(
                    status_code=429,
                    body=json.dumps(
                        [make_error_body("quota", LONG_RETRY_DELAY)]
                    ).encode(),
                ),
                expected_delay=10330.0,
            ),
            id="gemini_list_body",
        ),
        pytest.param(
            Scenario(
                response=make_response(
                    status_code=429,
                    body=json.dumps(make_error_body("quota", "7s")).encode(),
                ),
                expected_delay=7.0,
            ),
            id="dict_body",
        ),
        pytest.param(
            Scenario(
                response=make_response(status_code=429, headers={"Retry-After": "3"}),
                expected_delay=3.0,
            ),
            id="retry_after_header",
        ),
        pytest.param(
            Scenario(
                response=make_response(
                    status_code=429,
                    body=json.dumps(make_error_body("quota")).encode(),
                ),
                expected_delay=None,
            ),
            id="no_retry_info",
        ),
        pytest.param(
            Scenario(
                response=make_response(status_code=429, body=b"<html>slow down</html>"),
                expected_delay=None,
            ),
            id="non_json_body",
        ),
    ],
)
def test_server_retry_delay(scenario):
    """Checks that the server delay is read from header or body, or is None."""
    # given
    response = scenario.response

    # when
    delay = models.OpenAICompatibleProvider._server_retry_delay(response)

    # then
    assert delay == scenario.expected_delay


def test_raise_for_status_keeps_provider_message():
    """Checks that the provider message stays in the error, to tell causes apart."""
    # given
    message = "model is no longer available"
    response = make_response(
        status_code=404, body=json.dumps([{"error": {"message": message}}]).encode()
    )

    # when
    with pytest.raises(requests.HTTPError) as exc_info:
        models.OpenAICompatibleProvider._raise_for_status(response)

    # then
    assert message in str(exc_info.value)


@pytest.fixture
def quota_exhausted_server():
    """Local server that answers every chat request with a daily quota 429."""
    request_count = {"value": 0}
    body = json.dumps([make_error_body("daily quota", LONG_RETRY_DELAY)]).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            request_count["value"] += 1
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args, **kwargs):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", request_count
    server.shutdown()
    server.server_close()


def test_chat_fails_fast_on_long_server_retry_delay(quota_exhausted_server):
    """Checks that a long server delay raises at once, not after minutes of retries."""
    # given
    base_url, request_count = quota_exhausted_server
    provider = models.OpenAICompatibleProvider(base_url=base_url)

    # when
    with pytest.raises(requests.HTTPError):
        provider.chat(model="m", messages=[])

    # then
    assert request_count["value"] == 1

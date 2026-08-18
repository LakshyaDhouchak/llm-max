import requests

from llm_max.adapters.ollama import OllamaAdapter
from tests.fixtures.ollama_responses import (
    GENERATE_RESPONSE,
    GENERATE_RESPONSE_NO_TIMING,
    PULL_STREAM_LINES,
    TAGS_RESPONSE,
    TAGS_RESPONSE_EMPTY,
)


def _mock_response(mocker, json_data=None, status_code=200, iter_lines=None):
    resp = mocker.Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = mocker.Mock()
    if iter_lines is not None:
        resp.iter_lines.return_value = iter_lines
        resp.__enter__ = mocker.Mock(return_value=resp)
        resp.__exit__ = mocker.Mock(return_value=False)
    return resp


def test_is_available_true_when_server_responds(mocker):
    mocker.patch(
        "requests.get", return_value=_mock_response(mocker, TAGS_RESPONSE_EMPTY)
    )
    assert OllamaAdapter().is_available() is True


def test_is_available_false_when_server_unreachable(mocker):
    mocker.patch("requests.get", side_effect=requests.ConnectionError())
    assert OllamaAdapter().is_available() is False


def test_is_available_false_on_non_200(mocker):
    mocker.patch("requests.get", return_value=_mock_response(mocker, {}, status_code=500))
    assert OllamaAdapter().is_available() is False


def test_list_installed_parses_tags_response(mocker):
    mocker.patch("requests.get", return_value=_mock_response(mocker, TAGS_RESPONSE))
    models = OllamaAdapter().list_installed()

    assert len(models) == 2
    assert models[0].id == "llama3.1:8b"
    assert models[0].size_mb == TAGS_RESPONSE["models"][0]["size"] // (1024 * 1024)
    assert models[0].digest == "sha256:abc123"


def test_list_installed_empty(mocker):
    mocker.patch("requests.get", return_value=_mock_response(mocker, TAGS_RESPONSE_EMPTY))
    assert OllamaAdapter().list_installed() == []


def test_pull_yields_progress_events(mocker):
    mocker.patch(
        "requests.post",
        return_value=_mock_response(mocker, iter_lines=PULL_STREAM_LINES),
    )
    events = list(OllamaAdapter().pull("llama3.1:8b"))

    assert len(events) == len(PULL_STREAM_LINES)
    assert events[0]["status"] == "pulling manifest"
    assert events[-1]["status"] == "success"


def test_run_computes_tokens_per_sec(mocker):
    mocker.patch(
        "requests.post", return_value=_mock_response(mocker, GENERATE_RESPONSE)
    )
    result = OllamaAdapter().run("llama3.1:8b", "hello")

    assert result["response"] == GENERATE_RESPONSE["response"]
    assert result["tokens_generated"] == 42
    # 42 tokens / 2.1s = 20 tok/s
    assert result["tokens_per_sec"] == 20.0


def test_run_handles_zero_duration_gracefully(mocker):
    mocker.patch(
        "requests.post",
        return_value=_mock_response(mocker, GENERATE_RESPONSE_NO_TIMING),
    )
    result = OllamaAdapter().run("llama3.1:8b", "hi")

    assert result["tokens_per_sec"] is None
    assert result["tokens_generated"] == 0
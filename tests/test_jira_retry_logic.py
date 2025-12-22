"""Test retry behavior for various failure scenarios."""
import pytest
import responses
from jira_config import get_jira_session

@responses.activate
def test_retry_on_500_error(mock_jira_env):
    """Verify retries occur on 500 Internal Server Error."""
    url = "https://test.atlassian.net/rest/api/3/issue/TEST-1"

    # First 2 attempts fail with 500, 3rd succeeds
    responses.add(responses.GET, url, status=500, json={"error": "Server Error"})
    responses.add(responses.GET, url, status=500, json={"error": "Server Error"})
    responses.add(responses.GET, url, status=200, json={"key": "TEST-1", "fields": {}})

    session = get_jira_session()
    resp = session.get(url, timeout=15)

    assert resp.status_code == 200
    assert len(responses.calls) == 3, "Should retry twice before success"

@responses.activate
def test_retry_on_503_error(mock_jira_env):
    """Verify retries occur on 503 Service Unavailable."""
    url = "https://test.atlassian.net/rest/api/3/issue/TEST-2"
    responses.add(responses.GET, url, status=503)
    responses.add(responses.GET, url, status=200, json={"key": "TEST-2"})

    session = get_jira_session()
    resp = session.get(url, timeout=15)

    assert resp.status_code == 200
    assert len(responses.calls) == 2

@responses.activate
def test_retry_on_429_rate_limit(mock_jira_env):
    """Verify retries occur on 429 rate limit with exponential backoff."""
    url = "https://test.atlassian.net/rest/api/3/issue/TEST-3"
    responses.add(responses.GET, url, status=429, headers={"Retry-After": "1"})
    responses.add(responses.GET, url, status=200, json={"key": "TEST-3"})

    session = get_jira_session()
    resp = session.get(url, timeout=15)

    assert resp.status_code == 200
    assert len(responses.calls) == 2

@responses.activate
def test_no_retry_on_404(mock_jira_env):
    """Verify no retries on 404 Not Found (client error)."""
    url = "https://test.atlassian.net/rest/api/3/issue/NONEXISTENT"
    responses.add(responses.GET, url, status=404, json={"error": "Not Found"})

    session = get_jira_session()
    resp = session.get(url, timeout=15)

    assert resp.status_code == 404
    assert len(responses.calls) == 1, "Should not retry on client errors"

@responses.activate
def test_no_retry_on_401(mock_jira_env):
    """Verify no retries on 401 Unauthorized (client error)."""
    url = "https://test.atlassian.net/rest/api/3/issue/TEST-4"
    responses.add(responses.GET, url, status=401, json={"error": "Unauthorized"})

    session = get_jira_session()
    resp = session.get(url, timeout=15)

    assert resp.status_code == 401
    assert len(responses.calls) == 1

@responses.activate
def test_retry_exhaustion(mock_jira_env):
    """Verify behavior after all retries exhausted."""
    url = "https://test.atlassian.net/rest/api/3/issue/TEST-5"

    # Return 500 for all 5 attempts (initial + 4 retries)
    for _ in range(5):
        responses.add(responses.GET, url, status=500)

    session = get_jira_session()
    resp = session.get(url, timeout=15)

    assert resp.status_code == 500
    assert len(responses.calls) == 5, "Should exhaust all retries"

@responses.activate
def test_post_request_retry(mock_jira_env):
    """Verify POST requests also retry on 5xx (new feature)."""
    url = "https://test.atlassian.net/rest/api/3/search"
    responses.add(responses.POST, url, status=503)
    responses.add(responses.POST, url, status=200, json={"issues": [], "total": 0})

    session = get_jira_session()
    resp = session.post(url, json={"jql": "project=TEST"}, timeout=15)

    assert resp.status_code == 200
    assert len(responses.calls) == 2, "POST should also retry"

@responses.activate
def test_put_request_retry(mock_jira_env):
    """Verify PUT requests also retry on 5xx (new feature)."""
    url = "https://test.atlassian.net/rest/api/3/issue/TEST-6"
    responses.add(responses.PUT, url, status=502)
    responses.add(responses.PUT, url, status=200, json={"key": "TEST-6"})

    session = get_jira_session()
    resp = session.put(url, json={"fields": {"labels": ["test"]}}, timeout=15)

    assert resp.status_code == 200
    assert len(responses.calls) == 2, "PUT should also retry"

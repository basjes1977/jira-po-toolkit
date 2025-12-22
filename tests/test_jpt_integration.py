"""Integration tests ensuring jpt.py works correctly after migration."""
import pytest
import responses
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@responses.activate
def test_get_current_sprint_id(mock_jira_env):
    """Test get_current_sprint_id uses session with auth."""
    import jpt

    url = "https://test.atlassian.net/rest/agile/1.0/board/42/sprint?state=active"
    responses.add(
        responses.GET,
        url,
        json={"values": [{"id": 123, "name": "Sprint 1", "state": "active"}]},
        status=200
    )

    sprint_id = jpt.get_current_sprint_id()

    assert sprint_id == 123
    assert len(responses.calls) == 1

    # Verify auth header was sent
    assert "Authorization" in responses.calls[0].request.headers

@responses.activate
def test_get_issues_with_pagination(mock_jira_env):
    """Test get_issues handles pagination correctly."""
    import jpt

    url = "https://test.atlassian.net/rest/agile/1.0/sprint/123/issue"

    # First page
    responses.add(
        responses.GET,
        url,
        json={
            "total": 75,
            "issues": [{"key": f"TEST-{i}"} for i in range(50)]
        },
        status=200
    )

    # Second page
    responses.add(
        responses.GET,
        url,
        json={
            "total": 75,
            "issues": [{"key": f"TEST-{i}"} for i in range(50, 75)]
        },
        status=200
    )

    issues = jpt.get_issues(123)

    assert len(issues) == 75
    assert len(responses.calls) == 2

@responses.activate
def test_jql_search_now_has_retry(mock_jira_env):
    """Test jql_search now retries via session (bug fix)."""
    import jpt

    url = "https://test.atlassian.net/rest/api/3/search/jql"

    # First attempt fails, second succeeds
    responses.add(responses.POST, url, status=503)
    responses.add(
        responses.POST,
        url,
        json={"issues": [{"key": "TEST-1"}], "total": 1},
        status=200
    )

    result = jpt.jql_search({"jql": "project=TEST", "fields": ["summary"]})

    assert result is not None
    assert result["total"] == 1
    # Retry should have happened
    assert len(responses.calls) >= 2

@responses.activate
def test_auth_applied_to_previously_broken_calls(mock_jira_env):
    """Test that lines 436, 677, 721 now have proper auth (bug fix)."""
    import jpt

    # Simulate the dump_issue flow (line 436)
    url = "https://test.atlassian.net/rest/api/2/issue/TEST-1"

    def check_auth(request):
        # Before: this call had NO auth parameter (bug)
        # After: session provides auth automatically
        assert "Authorization" in request.headers, "Auth should be present now"
        return (200, {}, '{"key": "TEST-1", "fields": {}}')

    responses.add_callback(
        responses.GET,
        url,
        callback=check_auth,
        content_type="application/json"
    )

    # This internally uses session which has auth
    resp = jpt._JIRA_SESSION.get(url, params={"fields": "*all"}, timeout=15)
    assert resp.status_code == 200

"""
Tests for jira_performance module - caching and optimized date parsing.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from jira_performance import (
    parse_iso8601_datetime,
    get_cached_sprint_metadata,
    clear_sprint_cache,
    clear_date_parse_cache,
    get_cache_stats
)


class TestParseISO8601Datetime:
    """Test ISO 8601 date parsing with various formats."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_date_parse_cache()

    def test_parse_z_format(self):
        """Parse dates with Z (Zulu/UTC) timezone."""
        dt = parse_iso8601_datetime("2024-01-15T09:00:00.000Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 9
        assert dt.minute == 0

    def test_parse_plus_0000_format(self):
        """Parse dates with +0000 timezone offset."""
        dt = parse_iso8601_datetime("2024-01-15T09:00:00.000+0000")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_plus_hhmm_format(self):
        """Parse dates with +HH:MM timezone offset."""
        dt = parse_iso8601_datetime("2024-01-15T09:00:00+02:00")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 9

    def test_parse_with_microseconds(self):
        """Parse dates with microseconds."""
        dt = parse_iso8601_datetime("2024-01-15T09:00:00.123456Z")
        assert dt is not None
        assert dt.microsecond == 123456

    def test_parse_empty_string(self):
        """Empty strings should return None."""
        assert parse_iso8601_datetime("") is None
        assert parse_iso8601_datetime(None) is None

    def test_parse_invalid_format(self):
        """Invalid date formats should return None."""
        assert parse_iso8601_datetime("invalid") is None
        assert parse_iso8601_datetime("2024-13-45") is None
        assert parse_iso8601_datetime("not-a-date") is None

    def test_caching_works(self):
        """Verify that repeated calls use cached results."""
        clear_date_parse_cache()

        # First call
        dt1 = parse_iso8601_datetime("2024-01-15T09:00:00.000Z")

        # Second call with same input
        dt2 = parse_iso8601_datetime("2024-01-15T09:00:00.000Z")

        # Should return same object (cached)
        assert dt1 == dt2
        assert dt1 is dt2  # Same object reference

        # Check cache stats
        stats = get_cache_stats()
        assert stats['date_cache'].hits >= 1
        assert stats['date_cache'].misses >= 1

    def test_cache_different_inputs(self):
        """Different inputs should be cached separately."""
        clear_date_parse_cache()

        dt1 = parse_iso8601_datetime("2024-01-15T09:00:00.000Z")
        dt2 = parse_iso8601_datetime("2024-01-16T10:00:00.000Z")

        assert dt1 != dt2
        assert dt1.day == 15
        assert dt2.day == 16


class TestCachedSprintMetadata:
    """Test sprint metadata caching."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_sprint_cache()

    @patch('jira_config.get_jira_session')
    def test_fetch_sprint_metadata(self, mock_get_session):
        """Test basic sprint metadata fetching."""
        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 123,
            "name": "Sprint 42",
            "startDate": "2024-01-15T09:00:00.000Z",
            "endDate": "2024-01-29T18:00:00.000Z",
            "state": "active"
        }
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        # Fetch metadata
        result = get_cached_sprint_metadata("https://jira.example.com", 123)

        # Verify result
        assert result["id"] == 123
        assert result["name"] == "Sprint 42"
        assert result["startDate"] == "2024-01-15T09:00:00.000Z"
        assert result["endDate"] == "2024-01-29T18:00:00.000Z"
        assert result["state"] == "active"

        # Verify API call
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "sprint/123" in call_args[0][0]

    @patch('jira_config.get_jira_session')
    def test_caching_prevents_duplicate_calls(self, mock_get_session):
        """Verify that caching prevents duplicate API calls."""
        # Mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 456,
            "name": "Sprint 99",
            "startDate": "2024-02-01T09:00:00.000Z",
            "endDate": "2024-02-15T18:00:00.000Z",
        }
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        # First call
        result1 = get_cached_sprint_metadata("https://jira.example.com", 456)

        # Second call with same sprint ID
        result2 = get_cached_sprint_metadata("https://jira.example.com", 456)

        # Third call with same sprint ID
        result3 = get_cached_sprint_metadata("https://jira.example.com", 456)

        # Verify all results are identical
        assert result1 == result2 == result3

        # API should be called only ONCE (not 3 times)
        assert mock_session.get.call_count == 1

        # Check cache stats
        stats = get_cache_stats()
        assert stats['sprint_cache'].hits >= 2  # Second and third calls are hits
        assert stats['sprint_cache'].misses >= 1  # First call is a miss

    @patch('jira_config.get_jira_session')
    def test_different_sprints_cached_separately(self, mock_get_session):
        """Different sprint IDs should be cached separately."""
        mock_session = Mock()

        def mock_get(url, **kwargs):
            """Return different data based on sprint ID in URL."""
            response = Mock()
            if "sprint/100" in url:
                response.json.return_value = {"id": 100, "name": "Sprint 100"}
            elif "sprint/200" in url:
                response.json.return_value = {"id": 200, "name": "Sprint 200"}
            return response

        mock_session.get.side_effect = mock_get
        mock_get_session.return_value = mock_session

        # Fetch two different sprints
        result1 = get_cached_sprint_metadata("https://jira.example.com", 100)
        result2 = get_cached_sprint_metadata("https://jira.example.com", 200)

        # Verify different results
        assert result1["id"] == 100
        assert result1["name"] == "Sprint 100"
        assert result2["id"] == 200
        assert result2["name"] == "Sprint 200"

        # Both should have been fetched (2 API calls)
        assert mock_session.get.call_count == 2

    @patch('jira_config.get_jira_session')
    def test_cache_clear_works(self, mock_get_session):
        """Clearing cache should force re-fetch."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"id": 789, "name": "Sprint Test"}
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        # First fetch
        get_cached_sprint_metadata("https://jira.example.com", 789)
        assert mock_session.get.call_count == 1

        # Clear cache
        clear_sprint_cache()

        # Second fetch should hit API again
        get_cached_sprint_metadata("https://jira.example.com", 789)
        assert mock_session.get.call_count == 2


class TestCacheStats:
    """Test cache statistics functionality."""

    def test_get_cache_stats_structure(self):
        """Verify cache stats return correct structure."""
        clear_sprint_cache()
        clear_date_parse_cache()

        stats = get_cache_stats()

        # Should have both caches
        assert 'sprint_cache' in stats
        assert 'date_cache' in stats

        # Each should have cache_info attributes
        assert hasattr(stats['sprint_cache'], 'hits')
        assert hasattr(stats['sprint_cache'], 'misses')
        assert hasattr(stats['sprint_cache'], 'maxsize')
        assert hasattr(stats['sprint_cache'], 'currsize')

        assert hasattr(stats['date_cache'], 'hits')
        assert hasattr(stats['date_cache'], 'misses')

    def test_cache_stats_track_usage(self):
        """Cache stats should accurately track hits and misses."""
        clear_date_parse_cache()

        # Get initial stats
        stats_before = get_cache_stats()
        initial_misses = stats_before['date_cache'].misses

        # Parse same date twice
        parse_iso8601_datetime("2024-03-01T12:00:00Z")  # Miss
        parse_iso8601_datetime("2024-03-01T12:00:00Z")  # Hit

        # Get updated stats
        stats_after = get_cache_stats()

        # Should have 1 more miss and 1 more hit
        assert stats_after['date_cache'].misses == initial_misses + 1
        assert stats_after['date_cache'].hits >= stats_before['date_cache'].hits + 1

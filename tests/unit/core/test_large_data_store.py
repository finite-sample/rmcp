#!/usr/bin/env python3
"""Bounds on the oversized-result store.

Results too large to inline are parked behind an ``rmcp://data/{id}`` link.
Each is at least 50KB, so the store has to evict; an unbounded one grows for
the life of the process, which matters for the long-running HTTP server.
"""

from urllib.parse import urlparse

import pytest
from rmcp.core.context import Context, LifespanState
from rmcp.registries.resources import ResourcesRegistry
from rmcp.registries.tools import MAX_STORED_RESULTS, ToolsRegistry


def _oversized_payload():
    """Comfortably past both the 50KB and 1000-row thresholds."""
    return {"col_a": list(range(20000)), "col_b": list(range(20000))}


def _store_one(registry):
    uri = registry._check_for_large_data_and_create_resource(_oversized_payload())
    assert uri is not None, "payload should have been diverted to a resource link"
    return uri


class TestLargeDataStoreEviction:
    def test_store_stays_bounded(self):
        registry = ToolsRegistry()
        for _ in range(MAX_STORED_RESULTS + 10):
            _store_one(registry)

        assert len(registry._large_data_store) == MAX_STORED_RESULTS

    def test_oldest_entries_are_evicted_first(self):
        registry = ToolsRegistry()
        uris = [_store_one(registry) for _ in range(MAX_STORED_RESULTS + 5)]

        oldest = uris[0].rsplit("/", 1)[1]
        newest = uris[-1].rsplit("/", 1)[1]

        assert oldest not in registry._large_data_store
        assert newest in registry._large_data_store

    def test_small_payloads_are_not_stored(self):
        registry = ToolsRegistry()
        assert (
            registry._check_for_large_data_and_create_resource({"x": [1, 2, 3]}) is None
        )
        assert len(registry._large_data_store) == 0


class TestExpiredResourceLink:
    @pytest.mark.asyncio
    async def test_evicted_link_explains_itself(self):
        """An expired link must say it expired, not look like a bad URI."""
        registry = ToolsRegistry()
        uris = [_store_one(registry) for _ in range(MAX_STORED_RESULTS + 5)]

        class _Server:
            tools = registry

        context = Context.create("test", "test", LifespanState())

        with pytest.raises(ValueError) as excinfo:
            await ResourcesRegistry()._read_stored_rmcp_data(
                context, _Server(), urlparse(uris[0])
            )

        message = str(excinfo.value)
        assert "no longer available" in message
        assert str(MAX_STORED_RESULTS) in message

    @pytest.mark.asyncio
    async def test_live_link_still_resolves(self):
        registry = ToolsRegistry()
        uri = _store_one(registry)

        class _Server:
            tools = registry

        context = Context.create("test", "test", LifespanState())
        result = await ResourcesRegistry()._read_stored_rmcp_data(
            context, _Server(), urlparse(uri)
        )

        assert result["contents"][0]["mimeType"] == "application/json"
        assert "col_a" in result["contents"][0]["text"]

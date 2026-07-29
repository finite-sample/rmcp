#!/usr/bin/env python3
"""The shape of emitted log lines.

Regression cover for a configuration where structlog rendered JSON and a second
formatter nested that string under ``message``, so every structured field was
trapped inside an escaped string and nothing was queryable. Shape is asserted
rather than eyeballed because that failure looks fine at a glance.
"""

import contextlib
import io
import json
import logging

import pytest
from rmcp.logging_config import (
    configure_structured_logging,
    get_logger,
    request_id_var,
    set_request_id,
)


def _emit(fn, **kwargs) -> list[dict]:
    """Run `fn`, returning the JSON log lines it produced on stderr."""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        configure_structured_logging(level="INFO", **kwargs)
        fn()
    return [json.loads(line) for line in buf.getvalue().strip().splitlines() if line]


@pytest.fixture(autouse=True)
def _reset_request_id():
    token = request_id_var.set(None)
    yield
    request_id_var.reset(token)


class TestSingleEncoding:
    def test_fields_are_top_level_not_nested_in_a_string(self):
        """The regression: fields must not be buried in an escaped JSON string."""
        lines = _emit(
            lambda: get_logger("rmcp.demo").info(
                "tool completed", tool="linear_model", duration_ms=42
            )
        )
        assert len(lines) == 1
        entry = lines[0]

        assert entry["tool"] == "linear_model"
        assert entry["duration_ms"] == 42
        assert entry["event"] == "tool completed"

    def test_no_field_value_is_itself_json(self):
        """A double-encoded line hides a whole JSON object inside one value."""
        lines = _emit(
            lambda: get_logger("rmcp.demo").info("hello", tool="x", duration_ms=1)
        )
        for value in lines[0].values():
            if isinstance(value, str) and value.startswith("{"):
                with pytest.raises(json.JSONDecodeError):
                    json.loads(value)


class TestOneShape:
    def test_structlog_and_stdlib_share_an_envelope(self):
        """The 10 modules on plain `logging` must not emit a second shape."""

        def emit_both():
            get_logger("rmcp.demo").info("from structlog")
            logging.getLogger("rmcp.core.server").info("from stdlib")

        lines = _emit(emit_both)
        assert len(lines) == 2
        envelope = {"event", "level", "component", "timestamp", "service", "protocol"}
        for entry in lines:
            assert envelope <= set(entry), f"missing {envelope - set(entry)}"

    def test_component_strips_the_package_prefix(self):
        lines = _emit(lambda: logging.getLogger("rmcp.core.server").info("x"))
        assert lines[0]["component"] == "core.server"


class TestRequestIdPropagation:
    def test_absent_when_no_request_is_in_scope(self):
        lines = _emit(lambda: get_logger("rmcp.demo").info("no request"))
        assert "request_id" not in lines[0]

    def test_present_on_every_line_once_set(self):
        """This is what ties a tool call to the R execution beneath it."""

        def emit():
            set_request_id("req-42")
            get_logger("rmcp.demo").info("structlog line")
            logging.getLogger("rmcp.core.server").info("stdlib line")

        lines = _emit(emit)
        assert [entry.get("request_id") for entry in lines] == ["req-42", "req-42"]


class TestStdoutIsNeverWritten:
    def test_output_goes_to_stderr(self):
        """stdout carries the JSON-RPC stream in stdio mode."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            configure_structured_logging(level="INFO")
            get_logger("rmcp.demo").info("should not reach stdout")

        assert out.getvalue() == ""
        assert "should not reach stdout" in err.getvalue()

"""Cursor/limit pagination used by every registry's list call."""

import pytest
from rmcp.registries._pagination import paginate_items

ITEMS = ["a", "b", "c", "d", "e"]


@pytest.mark.parametrize(
    ("cursor", "limit", "page", "next_cursor"),
    [
        (None, None, ["a", "b", "c", "d", "e"], None),
        (None, 2, ["a", "b"], "2"),
        ("2", 2, ["c", "d"], "4"),
        ("4", 2, ["e"], None),
        ("3", None, ["d", "e"], None),
        ("5", None, [], None),
        ("0", 10, ["a", "b", "c", "d", "e"], None),
    ],
)
def test_pages(cursor, limit, page, next_cursor):
    assert paginate_items(ITEMS, cursor, limit) == (page, next_cursor)


def test_walking_the_cursor_visits_every_item_once():
    seen, cursor = [], None
    while True:
        page, cursor = paginate_items(ITEMS, cursor, 2)
        seen += page
        if cursor is None:
            break
    assert seen == ITEMS


def test_empty_listing_has_one_empty_page():
    assert paginate_items([], None, 3) == ([], None)


@pytest.mark.parametrize(
    ("cursor", "limit", "message"),
    [
        (3, None, "cursor must be a string if provided"),
        ("x", None, "cursor must be an integer string"),
        ("-1", None, "cursor is out of range"),
        ("6", None, "cursor is out of range"),
        (None, "many", "limit must be an integer"),
        (None, 0, "limit must be a positive integer"),
        (None, -2, "limit must be a positive integer"),
    ],
)
def test_bad_arguments(cursor, limit, message):
    with pytest.raises(ValueError, match=message):
        paginate_items(ITEMS, cursor, limit)

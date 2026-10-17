"""Cursor/limit pagination shared by the tool, resource and prompt registries."""


def paginate_items[T](
    items: list[T], cursor: str | None, limit: int | None
) -> tuple[list[T], str | None]:
    """Return one page of ``items`` and the cursor for the next page.

    The cursor is the index of the first item on the page, as a string.

    Args:
        items: Everything that can be listed, in listing order.
        cursor: Index to start from, as returned by the previous page.
        limit: Largest page size, or ``None`` for everything after ``cursor``.

    Returns:
        The page, and the next page's cursor or ``None`` on the last page.

    Raises:
        ValueError: If ``cursor`` is not an in-range integer string, or
            ``limit`` is not a positive integer.
    """
    total_items = len(items)
    start_index = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise ValueError("cursor must be a string if provided")
        try:
            start_index = int(cursor)
        except ValueError as exc:
            raise ValueError("cursor must be an integer string") from exc
        if start_index < 0 or start_index > total_items:
            raise ValueError("cursor is out of range")
    if limit is not None:
        try:
            limit_value = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValueError("limit must be an integer") from exc
        if limit_value <= 0:
            raise ValueError("limit must be a positive integer")
    else:
        limit_value = total_items - start_index
    end_index = min(start_index + limit_value, total_items)
    next_cursor = str(end_index) if end_index < total_items else None
    return items[start_index:end_index], next_cursor

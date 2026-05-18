from utils import format_date_display, parse_date_input


def test_parse_dd_mm_yyyy():
    assert parse_date_input("18-05-2026").isoformat() == "2026-05-18"


def test_format_display():
    from datetime import date

    assert format_date_display(date(2026, 5, 18)) == "18-05-2026"

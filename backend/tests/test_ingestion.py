import pytest
from app.utils.text_norm import parse_raw_transcript_text, parse_timestamp_str_to_ms
from app.utils.hashing import compute_transcript_hash, compute_idempotency_key


def test_parse_timestamp_str():
    assert parse_timestamp_str_to_ms("00:15") == 15000
    assert parse_timestamp_str_to_ms("01:30") == 90000
    assert parse_timestamp_str_to_ms("01:00:00") == 3600000
    assert parse_timestamp_str_to_ms("45s") == 45000


def test_parse_raw_transcript_bracket_format():
    raw = """
    [00:00 - 00:05] Rahul: Rahul will implement OAuth backend by Friday.
    [00:06 - 00:10] Priya: Priya will add the login UI.
    """
    segments = parse_raw_transcript_text(raw)
    assert len(segments) == 2
    assert segments[0]["speaker_name"] == "Rahul"
    assert segments[0]["start_ms"] == 0
    assert segments[0]["end_ms"] == 5000
    assert "OAuth" in segments[0]["text"]
    assert segments[1]["speaker_name"] == "Priya"


def test_transcript_hash_idempotency():
    seg1 = [{"speaker_name": "Rahul", "start_ms": 0, "end_ms": 5000, "text": "OAuth backend by Friday"}]
    seg2 = [{"speaker_name": "Rahul", "start_ms": 0, "end_ms": 5000, "text": "OAuth backend by Friday"}]
    seg3 = [{"speaker_name": "Rahul", "start_ms": 0, "end_ms": 5000, "text": "Different text"}]

    hash1 = compute_transcript_hash(seg1)
    hash2 = compute_transcript_hash(seg2)
    hash3 = compute_transcript_hash(seg3)

    assert hash1 == hash2
    assert hash1 != hash3


def test_idempotency_key_generation():
    key1 = compute_idempotency_key("meet_1", "task_oauth:friday", "CREATE_ISSUE")
    key2 = compute_idempotency_key("meet_1", "task_oauth:friday", "CREATE_ISSUE")
    key3 = compute_idempotency_key("meet_2", "task_oauth:friday", "CREATE_ISSUE")

    assert key1 == key2
    assert key1 != key3

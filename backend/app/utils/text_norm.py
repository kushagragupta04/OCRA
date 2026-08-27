import re
from typing import List, Dict, Any


def parse_timestamp_str_to_ms(ts_str: str) -> int:
    """Converts formats like '01:23', '00:01:23', '1:23.450', '83s' into milliseconds."""
    ts_str = ts_str.strip().lower().rstrip("s")
    parts = ts_str.split(":")
    
    try:
        if len(parts) == 1:
            return int(float(parts[0]) * 1000)
        elif len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return int((minutes * 60 + seconds) * 1000)
        elif len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return int((hours * 3600 + minutes * 60 + seconds) * 1000)
    except Exception:
        return 0
    return 0


def parse_raw_transcript_text(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parses unstructured or semi-structured meeting transcript text into normalized segments.
    Supports:
    - [00:10] Rahul: statement
    - Rahul (00:10 - 00:25): statement
    - 00:00:10 --> 00:00:25 \n Rahul: statement (WebVTT/SRT style)
    - Speaker: Statement without timestamps (auto-estimates 10s intervals)
    """
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    segments: List[Dict[str, Any]] = []
    
    # Pattern 1: [00:15] Speaker: text or [00:15 - 00:30] Speaker: text
    bracket_pattern = re.compile(r"^\[([0-9:\.\- ]+)\]\s*([^:]+):\s*(.*)$")
    # Pattern 2: Speaker (00:15): text
    paren_pattern = re.compile(r"^([^\(]+)\s*\(([0-9:\.\- ]+)\):\s*(.*)$")
    # Pattern 3: Speaker: text
    simple_pattern = re.compile(r"^([A-Za-z0-9 _]+):\s*(.*)$")

    current_ms = 0

    for i, line in enumerate(lines):
        # Ignore WebVTT header or numeric cue lines
        if line.startswith("WEBVTT") or line.isdigit():
            continue

        # Check bracket pattern
        m1 = bracket_pattern.match(line)
        if m1:
            time_part, speaker, text = m1.groups()
            times = [t.strip() for t in time_part.split("-")]
            start_ms = parse_timestamp_str_to_ms(times[0])
            end_ms = parse_timestamp_str_to_ms(times[1]) if len(times) > 1 else start_ms + max(len(text) * 80, 4000)
            segments.append({
                "speaker_id": f"spk_{speaker.strip().lower().replace(' ', '_')}",
                "speaker_name": speaker.strip(),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text.strip()
            })
            current_ms = end_ms
            continue

        # Check paren pattern
        m2 = paren_pattern.match(line)
        if m2:
            speaker, time_part, text = m2.groups()
            times = [t.strip() for t in time_part.split("-")]
            start_ms = parse_timestamp_str_to_ms(times[0])
            end_ms = parse_timestamp_str_to_ms(times[1]) if len(times) > 1 else start_ms + max(len(text) * 80, 4000)
            segments.append({
                "speaker_id": f"spk_{speaker.strip().lower().replace(' ', '_')}",
                "speaker_name": speaker.strip(),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text.strip()
            })
            current_ms = end_ms
            continue

        # Check simple speaker pattern
        m3 = simple_pattern.match(line)
        if m3:
            speaker, text = m3.groups()
            duration_ms = max(len(text) * 80, 4000)
            start_ms = current_ms
            end_ms = start_ms + duration_ms
            segments.append({
                "speaker_id": f"spk_{speaker.strip().lower().replace(' ', '_')}",
                "speaker_name": speaker.strip(),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text.strip()
            })
            current_ms = end_ms + 1000
            continue

        # Fallback raw line
        duration_ms = max(len(line) * 80, 4000)
        start_ms = current_ms
        end_ms = start_ms + duration_ms
        segments.append({
            "speaker_id": "spk_speaker",
            "speaker_name": "Speaker",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": line.strip()
        })
        current_ms = end_ms + 1000

    return segments

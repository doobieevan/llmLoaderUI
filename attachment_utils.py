"""Bounded text attachment loading and prompt-context budgeting."""

from pathlib import Path

MAX_ATTACHMENT_FILE_BYTES = 8 * 1024 * 1024
DEFAULT_ATTACHMENT_CONTEXT_CHARS = 48_000


def load_text_attachment(path, max_bytes=MAX_ATTACHMENT_FILE_BYTES):
    target = Path(path)
    size = target.stat().st_size
    if size > max_bytes:
        raise ValueError(f"File is {size:,} bytes; limit is {max_bytes:,} bytes.")
    raw = target.read_bytes()
    if b"\x00" in raw:
        raise ValueError("Binary files are not supported as text attachments.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Attachment is not valid UTF-8 text.") from exc
    return target.name, text, size


def build_attachment_context(attachments, max_chars=DEFAULT_ATTACHMENT_CONTEXT_CHARS):
    """Assemble text attachments deterministically within a total character budget."""
    budget = max(0, int(max_chars))
    chunks = []
    remaining = budget
    omitted = 0
    for name, text in attachments:
        if remaining <= 0:
            omitted += 1
            continue
        header = f"--- {name} ---\n"
        room = remaining - len(header)
        if room <= 0:
            omitted += 1
            continue
        body = str(text)
        if len(body) > room:
            body = body[:room] + "\n[attachment truncated to fit context budget]"
            body = body[:room]
            omitted += 1
        piece = header + body
        chunks.append(piece)
        remaining -= len(piece) + 2
    if omitted and remaining >= 24:
        chunks.append(f"[{omitted} attachment(s) omitted or truncated by context budget]")
    return "\n\n".join(chunks), omitted

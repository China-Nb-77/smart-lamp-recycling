from __future__ import annotations

from typing import Any


def safe_load(stream: Any) -> Any:
    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = str(stream)
    lines = text.splitlines()
    index = 0

    def parse_block(indent: int) -> Any:
        nonlocal index
        mapping: dict[str, Any] = {}
        sequence: list[Any] | None = None

        while index < len(lines):
            raw_line = lines[index].rstrip()
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                index += 1
                continue

            current_indent = len(raw_line) - len(raw_line.lstrip(" "))
            if current_indent < indent:
                break
            if current_indent > indent:
                break

            line = raw_line[current_indent:]
            if line.startswith("- "):
                if sequence is None:
                    sequence = []
                value = line[2:].strip()
                index += 1
                if value:
                    sequence.append(parse_scalar(value))
                else:
                    sequence.append(parse_block(indent + 2))
                continue

            if sequence is not None:
                break

            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            index += 1
            if value:
                mapping[key] = parse_scalar(value)
            else:
                child = parse_block(indent + 2)
                mapping[key] = child

        if sequence is not None:
            return sequence
        return mapping

    return parse_block(0)


def dump(data: Any, stream: Any | None = None, **_: Any) -> str | None:
    text = _dump_value(data)
    if stream is not None:
        stream.write(text)
        return None
    return text


def safe_dump(data: Any, stream: Any | None = None, **kwargs: Any) -> str | None:
    return dump(data, stream=stream, **kwargs)


def load(stream: Any, **_: Any) -> Any:
    return safe_load(stream)


def parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None"}:
        return None
    if value == '""':
        return ""
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _dump_value(value: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_dump_value(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_dump_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_dump_value(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_dump_scalar(item)}")
        return "\n".join(lines)
    return f"{prefix}{_dump_scalar(value)}"


def _dump_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if any(ch in text for ch in [":", "#", "\n"]) or text.strip() != text:
        return f'"{text}"'
    return text

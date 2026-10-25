"""Минимальный разбор текстового Valve KeyValues (VDF) и точечная правка значений.

Правка (set_value) меняет только нужный фрагмент текста, поэтому остальной
localconfig.vdf остаётся байт-в-байт таким, каким его записал Steam.
"""

import re

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>//[^\n]*)
  | (?P<str>"(?:[^"\\]|\\.)*")
  | (?P<open>\{)
  | (?P<close>\})
  | (?P<word>[^\s{}"]+)
  | (?P<bad>.)
    """,
    re.VERBOSE | re.DOTALL,
)
_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def _unescape(raw):
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), "\\" + m.group(1)), raw, flags=re.DOTALL)


def escape(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def tokens(text):
    for match in _TOKEN_RE.finditer(text):
        kind = match.lastgroup
        if kind in ("ws", "comment", "bad"):
            continue
        if kind == "str":
            yield "str", _unescape(match.group()[1:-1]), match.start(), match.end()
        elif kind == "word":
            value = match.group()
            # условия вида [$WIN32] после значения
            yield ("cond" if value.startswith("[") and value.endswith("]") else "str"), value, match.start(), match.end()
        else:
            yield kind, None, match.start(), match.end()


class Block:
    __slots__ = ("key", "key_start", "open", "close", "items")

    def __init__(self, key, key_start, open_pos):
        self.key = key
        self.key_start = key_start
        self.open = open_pos
        self.close = None
        self.items = []


class Pair:
    __slots__ = ("key", "key_start", "value", "start", "end")

    def __init__(self, key, key_start, value, start, end):
        self.key = key
        self.key_start = key_start
        self.value = value
        self.start = start
        self.end = end


def parse_positions(text):
    root = Block("", 0, -1)
    stack = [root]
    key = None
    for kind, value, start, end in tokens(text):
        if kind == "cond":
            continue
        if kind == "str":
            if key is None:
                key = (value, start)
            else:
                stack[-1].items.append(Pair(key[0], key[1], value, start, end))
                key = None
        elif kind == "open":
            block = Block(key[0] if key else "", key[1] if key else start, start)
            stack[-1].items.append(block)
            stack.append(block)
            key = None
        elif kind == "close":
            if len(stack) > 1:
                stack.pop().close = start
            key = None
    for block in stack:
        if block.close is None:
            block.close = len(text)
    return root


def parse(text):
    """VDF → вложенные словари (повторяющиеся блоки объединяются)."""

    def convert(block):
        result = {}
        for item in block.items:
            if isinstance(item, Block):
                sub = convert(item)
                existing = result.get(item.key)
                if isinstance(existing, dict):
                    existing.update(sub)
                else:
                    result[item.key] = sub
            else:
                result[item.key] = item.value
        return result

    return convert(parse_positions(text))


def get(data, *keys):
    """Поиск по ключам без учёта регистра: get(d, "AppState", "UserConfig")."""
    for key in keys:
        if not isinstance(data, dict):
            return None
        low = key.lower()
        data = next((v for k, v in data.items() if k.lower() == low), None)
    return data


def find_block(block, keys):
    for key in keys:
        low = key.lower()
        block = next((it for it in block.items if isinstance(it, Block) and it.key.lower() == low), None)
        if block is None:
            return None
    return block


def get_value(text, block_keys, key):
    block = find_block(parse_positions(text), block_keys)
    if block is None:
        return None
    low = key.lower()
    pair = next((it for it in block.items if isinstance(it, Pair) and it.key.lower() == low), None)
    return pair.value if pair else None


def _insert_before_close(text, block, lines):
    """Вставляет строки перед закрывающей скобкой блока, сохраняя отступы Steam."""
    newline = "\r\n" if "\r\n" in text else "\n"
    line_start = text.rfind("\n", 0, block.close) + 1
    indent = text[line_start:block.close]
    if indent.strip():
        insert_at, indent, prefix = block.close, "", newline
    else:
        insert_at, prefix = line_start, ""
    payload = prefix + "".join(f"{indent}\t{line}{newline}" for line in lines)
    return text[:insert_at] + payload + text[insert_at:]


def set_value(text, block_keys, key, value):
    """Задаёт "key" "value" в блоке block_keys (последний блок создаётся при необходимости)."""
    root = parse_positions(text)
    quoted = f'"{escape(value)}"'
    block = find_block(root, block_keys)
    if block is None:
        parent = find_block(root, block_keys[:-1])
        if parent is None:
            raise KeyError("/".join(block_keys[:-1]))
        lines = [f'"{block_keys[-1]}"', "{", f'\t"{key}"\t\t{quoted}', "}"]
        return _insert_before_close(text, parent, lines)
    low = key.lower()
    pair = next((it for it in block.items if isinstance(it, Pair) and it.key.lower() == low), None)
    if pair is not None:
        return text[:pair.start] + quoted + text[pair.end:]
    return _insert_before_close(text, block, [f'"{key}"\t\t{quoted}'])

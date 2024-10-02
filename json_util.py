import json
import dataclasses

JSON_SEPARATOR = (",", ":")

# based on json.decoder.py_scanstring
def raw_scanstring(
    s,
    end,
    strict=True,
    _b=json.decoder.BACKSLASH,
    _m=json.decoder.STRINGCHUNK.match,
):
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise json.JSONDecodeError(
                "Unterminated string starting at", s, begin
            )
        end = chunk.end()
        content, terminator = chunk.groups()
        if content:
            _append(content)
        if terminator == '"':
            break
        elif terminator != "\\":
            if strict:
                msg = "Invalid control character {0!r} at".format(terminator)
                raise json.JSONDecodeError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise json.JSONDecodeError(
                "Unterminated string starting at", s, begin
            ) from None
        if esc != "u":
            try:
                char = _b[esc]
            except KeyError:
                msg = "Invalid \\escape: {0!r}".format(esc)
                raise json.JSONDecodeError(msg, s, end)
            end += 1
        else:
            # deleted unicode parsing code
            st = end - 1
            end += 5
            char = s[st:end]
        _append(char)
    return "".join(chunks), end


class JSONDecoderRawString(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parse_string = raw_scanstring
        self.scan_once = json.scanner.py_make_scanner(self)


class StructClassesJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            res = []
            for f in dataclasses.fields(o):
                value = getattr(o, f.name)
                if not (f.metadata.get("omitempty") and not value):
                    res.append((f.name, value))

            return dict(res)
        return super().default(o)

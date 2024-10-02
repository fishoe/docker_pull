import datetime
import hashlib
from pathlib import Path
import platform as os_platform

def date_parse(s: str) -> datetime.datetime:
    layout = "%Y-%m-%dT%H:%M:%S.%f%z"

    # remove Z at the end of the line
    if s.endswith("Z"):
        s = s[:-1]

    nano_s = 0
    datetime_parts = s.split(".")
    if len(datetime_parts) == 2:
        nano_s = datetime_parts[-1]
        # cut nanoseconds to microseconds
        if len(nano_s) > 6:
            nano_s = nano_s[:6]

    dt = "{}.{}+00:00".format(datetime_parts[0], nano_s)

    return datetime.datetime.strptime(dt, layout)


def www_auth(hdr: str) -> tuple[str, dict]:
    auth_scheme, info = hdr.split(" ", 1)

    out = {}
    for part in info.split(","):
        k, v = part.split("=", 1)
        out[k] = v.replace('"', "").strip()

    return auth_scheme, out


def sha256sum(name: str | Path, chunk_num_blocks: int = 128) -> str:
    h = hashlib.sha256()

    with open(name, "rb", buffering=0) as f:
        while chunk := f.read(chunk_num_blocks * h.block_size):
            h.update(chunk)

    return h.hexdigest()

def image_platform(s: str) -> tuple[str, str]:
    _os, arch = "linux", os_platform.machine()
    if s:
        _os, arch = s.split("/")

    return _os, arch

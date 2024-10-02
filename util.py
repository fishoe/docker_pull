import datetime
import hashlib
from pathlib import Path
import platform as os_platform
import struct
import gzip
import os
import tarfile

from tar_util import TarInfo
from progress_bar import ProgressBar, EmptyProgressBar

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


def unzip(
    zip_file_path: str | Path,
    out_file_path: str | Path,
    remove_zip_file: bool = True,
    progress: ProgressBar = EmptyProgressBar(),
):
    with gzip.open(zip_file_path, "rb") as zip_data, open(
        out_file_path, "wb"
    ) as unzip_data:
        zip_data.myfileobj.seek(-4, 2)
        size_bytes = zip_data.myfileobj.read(4)
        zip_data.myfileobj.seek(0)

        progress.set_size(struct.unpack("I", size_bytes)[0])

        done = 0
        while chunk := zip_data.read(131072):
            unzip_data.write(chunk)
            done += len(chunk)

            progress.write(done)

    if remove_zip_file:
        os.remove(zip_file_path)


def make_tar(out_path: Path, path: Path, created: float):
    tar = tarfile.open(out_path, "w")
    tar.tarinfo = TarInfo
    tar.format = tarfile.USTAR_FORMAT
    tarfile.RECORDSIZE = 512

    def mod(t: tarfile.TarInfo):
        t.uid = 0
        t.gid = 0
        t.uname = ""
        t.gname = ""

        if t.name in ["manifest.json", "repositories"]:
            t.mtime = 0
        else:
            t.mtime = created

        return t

    walk = []
    for d in path.iterdir():
        walk.append(d)

    for d in sorted(walk):
        tar.add(str(d.resolve()), str(d.relative_to(path)), filter=mod)

    tar.close()
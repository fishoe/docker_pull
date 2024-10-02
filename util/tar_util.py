import tarfile
import struct
import struct
import gzip
import os
from pathlib import Path

from progress_bar import ProgressBar, EmptyProgressBar

class TarInfo(tarfile.TarInfo):
    @staticmethod
    def _create_header(info, fmt, encoding, errors):
        parts = [
            tarfile.stn(info.get("name", ""), 100, encoding, errors),
            tarfile.itn(info.get("mode", 0) & 0o7777, 8, fmt),
            tarfile.itn(info.get("uid", 0), 8, fmt),
            tarfile.itn(info.get("gid", 0), 8, fmt),
            tarfile.itn(info.get("size", 0), 12, fmt),
            tarfile.itn(info.get("mtime", 0), 12, fmt),
            b"        ",  # checksum field
            info.get("type", tarfile.REGTYPE),
            tarfile.stn(info.get("linkname", ""), 100, encoding, errors),
            info.get("magic", tarfile.POSIX_MAGIC),
            tarfile.stn(info.get("uname", ""), 32, encoding, errors),
            tarfile.stn(info.get("gname", ""), 32, encoding, errors),
            tarfile.itn(info.get("devmajor", 0), 8, fmt),
            tarfile.itn(info.get("devminor", 0), 8, fmt),
            tarfile.stn(info.get("prefix", ""), 155, encoding, errors),
        ]

        buf = struct.pack("%ds" % tarfile.BLOCKSIZE, b"".join(parts))
        chksum = tarfile.calc_chksums(buf[-tarfile.BLOCKSIZE :])[0]

        return buf[:-364] + bytes("%06o\0" % chksum, "ascii") + buf[-357:]

def unzip(
    zip_file_path: str | Path,
    out_file_path: str | Path,
    remove_zip_file: bool = True,
    progress: ProgressBar = EmptyProgressBar(),
):
    with gzip.open(zip_file_path, "rb") as zip_data, \
            open(out_file_path, "wb") as unzip_data:
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
    with tarfile.open(out_path, "w") as tar:
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

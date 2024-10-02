import tarfile
import struct

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





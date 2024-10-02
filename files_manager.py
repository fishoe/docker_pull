from pathlib import Path


class FilesManager:
    def __init__(self, work_dir: str | Path):
        if isinstance(work_dir, str):
            work_dir = Path(work_dir)
        self._work_dir = work_dir
        self._work_dir.mkdir(0o755, True, True)

    def __call__(self, path: str):
        return FilesManager(self._join_path(Path(path)))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _join_path(self, p: Path) -> Path:
        path = self._work_dir.joinpath(p)
        path.resolve().relative_to(p.parent.resolve())

        return path

    def filepath(self, name: str) -> Path:
        return self._join_path(Path(name))

    def write(self, name: str, data: str | bytes):
        if isinstance(data, str):
            data = data.encode()

        with self.open(name, "wb") as f:
            f.write(data)

    def open(
        self,
        name: str | Path,
        mode="r",
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
    ):
        if isinstance(name, str):
            name = Path(name)

        path = self._join_path(name)
        if "w" in mode:
            path.parent.mkdir(0o755, True, True)

        return path.open(mode, buffering, encoding, errors, newline)

    @property
    def work_dir(self) -> Path:
        return self._work_dir.resolve()

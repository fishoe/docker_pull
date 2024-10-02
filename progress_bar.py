def sizeof_fmt(num: int) -> str:
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0

    return f"{num:3.2f}TiB"

class EmptyProgressBar:
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, item):
        def func(*args, **kwargs):
            pass

        return func


class ProgressBar:
    def __init__(self, progressbar_length: int = 96):
        self._end = "\r"
        self._description = ""
        self._content_sizeof_fmt = "0"
        self._content_size = 0
        self._progressbar_length = progressbar_length

    def set_size(self, size: int):
        self._content_sizeof_fmt = sizeof_fmt(size)
        self._content_size = size
        self._end = "\r"

        return self

    def update_description(self, s: str):
        self._description = s
        self._end = "\r"

        return self

    def flush(self, description: str):
        self.set_size(0)
        self.update_description(description)
        self._end = "\n"
        self.write(self._content_size)

    def write(self, done: int):
        size_fmt_length = 18
        fill = progressbar_fill_length = self._progressbar_length - (
            4 + len(self._description) + size_fmt_length
        )

        if self._content_size:
            fill = int(progressbar_fill_length * done / self._content_size)

        fill_suffix = "=" if progressbar_fill_length == fill else ">"
        progressbar_fill = "=" * (fill - 1) + fill_suffix

        if done and self._content_sizeof_fmt:
            tmpl = "{} [{:<{length}}] {:>{sizes}}"
            sizes = f"{sizeof_fmt(done)}/{self._content_sizeof_fmt}"
            progress_bar_str = tmpl.format(
                self._description,
                progressbar_fill,
                sizes,
                length=progressbar_fill_length,
                sizes=size_fmt_length,
            )
        else:
            fill = self._progressbar_length - len(self._description)
            progress_bar_str = f'{self._description}{" " * fill}'

        print(progress_bar_str, end=self._end, flush=True)

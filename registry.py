import requests
import requests.auth
import urllib.parse as urlparse
from pathlib import Path
import logging
import json
from progress_bar import ProgressBar, EmptyProgressBar
import os

from util import sha256sum, unzip, www_auth


class Registry:
    def __init__(
        self,
        credentials: requests.auth.HTTPBasicAuth = None,
        ssl: bool = True,
    ):
        self.__credentials = credentials
        self._ssl = ssl
        self._session = requests.Session()

    def _auth(self, resp: requests.Response):
        if not resp.headers.get("www-authenticate"):
            raise ValueError("empty the www-authenticate header")

        auth_scheme, parsed = www_auth(resp.headers["www-authenticate"])
        if auth_scheme.lower() == "basic":
            self.__credentials(self._session)
            return

        url_parts = list(urlparse.urlparse(parsed["realm"]))

        query = urlparse.parse_qs(url_parts[4])
        query.update(service=parsed["service"])
        scope = parsed.get("scope")
        if scope:
            query.update(scope=scope)

        url_parts[4] = urlparse.urlencode(query, True)

        r = self._session.get(
            urlparse.urlunparse(url_parts), auth=self.__credentials
        )
        r.raise_for_status()

        a_str = f"{auth_scheme} {r.json()['token']}"
        self._session.headers["Authorization"] = a_str

    def get(
        self, url: str, *, headers: dict = None, stream: bool = None
    ) -> requests.Response:
        if not url.startswith("http"):
            url = f"http{'s' if self._ssl else ''}://{url}"

        logging.debug("Request headers: %s", json.dumps(headers))
        r = self._session.get(url, headers=headers, stream=stream)
        if r.status_code == requests.codes.unauthorized:
            self._auth(r)
            r = self._session.get(url, headers=headers, stream=stream)

        if r.status_code != requests.codes.ok:
            logging.error(
                f"Status code: {r.status_code}, Response: {r.content}"
            )
            r.raise_for_status()

        logging.debug("Response headers: %s", json.dumps(r.headers.__dict__))
        if not stream:
            logging.debug("Response body: %s", r.content)

        return r

    def fetch_blob(
        self,
        url: str,
        out_file: Path,
        *,
        sha256: str = None,
        headers: dict = None,
        progress: ProgressBar = EmptyProgressBar(),
    ):

        mode = "wb"
        done = 0
        layer_id_short = os.path.basename(url)[7:19]
        temp_file = out_file.with_suffix(".gz")

        if temp_file.exists():
            done = temp_file.stat().st_size
            if done:
                logging.debug(f'resume download layer blob "{temp_file}"')
                mode = "ab"

            if sha256sum(temp_file) == sha256:
                if progress:
                    progress.flush(f"{layer_id_short}: Pull complete")

                logging.debug(f"File {temp_file} is up to date")
                return

            headers["Range"] = f"bytes={done}-"

        progress.update_description(f"{layer_id_short}: Pulling fs layer")
        progress.set_size(0)
        progress.write(0)

        r = self.get(url, headers=headers, stream=True)

        progress.update_description(f"{layer_id_short}: Downloading")
        progress.set_size(int(r.headers.get("Content-Length", 0)))

        with open(temp_file, mode) as f:
            for chunk in r.iter_content(chunk_size=131072):
                if chunk:
                    f.write(chunk)
                    done += len(chunk)

                    if progress:
                        progress.write(done)

        progress.update_description(f"{layer_id_short}: Extracting")

        unzip(temp_file, out_file, progress=progress)

        progress.flush(f"{layer_id_short}: Pull complete")

import argparse
import getpass
import logging
import sys
from pathlib import Path

from progress_bar import ProgressBar, EmptyProgressBar
from container_image import ImageFetcher, ImageParser


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="docker_pull.py",
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=36, width=120
        ),
    )

    parser.add_argument("images", nargs="+")

    parser.add_argument(
        "--output", "-o", default="output", type=Path, help="Output dir"
    )
    parser.add_argument(
        "--save-cache",
        action="store_true",
        help="Do not delete the temp folder",
    )
    parser.add_argument("--registry", "-r", type=str, help="Registry")
    parser.add_argument("--user", "-u", type=str, help="Registry login")
    parser.add_argument(
        "--platform",
        type=str,
        default="linux/amd64",
        help="Set platform for downloaded image",
    )

    verbose_grp = parser.add_mutually_exclusive_group()
    verbose_grp.add_argument(
        "--silent", "-s", action="store_true", help="Silent mode"
    )
    verbose_grp.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug output"
    )

    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--password", "-p", type=str, help="Registry password")
    grp.add_argument(
        "--stdin-password",
        "-P",
        action="store_true",
        help="Registry password (interactive)",
    )
    parsed_args = parser.parse_args()

    if parsed_args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if parsed_args.silent or parsed_args.verbose:
        _progress = EmptyProgressBar()
    else:
        _progress = ProgressBar()

    puller = ImageFetcher(
        parsed_args.output,
        progress=_progress,
        save_cache=parsed_args.save_cache,
    )

    if parsed_args.user:
        _password = parsed_args.password
        if parsed_args.stdin_password:
            std = sys.stdin
            if sys.stdin.isatty():
                _password = getpass.getpass()
            else:
                _password = sys.stdin.readline().strip()

        puller.set_registry(
            parsed_args.registry or ImageParser.REGISTRY_HOST,
            parsed_args.user,
            _password,
        )

    for _image in parsed_args.images:
        puller.pull(_image, parsed_args.platform)

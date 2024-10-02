import os
import hashlib
from pathlib import Path
import requests
import json
import shutil

from registry import Registry
from posixpath import join as path_join
from progress_bar import EmptyProgressBar, ProgressBar
from files_manager import FilesManager
from util.json_util import JSONDecoderRawString, JSON_SEPARATOR
from schemas import Manifest, ManifestList, V1Image, ContainerConfig, LayerConfig
from util import make_tar, date_parse, image_platform


def chain_ids(ids_list: list) -> list[str]:
    chain = list()
    chain.append(ids_list[0])

    if len(ids_list) < 2:
        return ids_list

    nxt = list()
    chain_b = f"{ids_list[0]} {ids_list[1]}".encode()
    nxt.append("sha256:" + hashlib.sha256(chain_b).hexdigest())
    nxt.extend(ids_list[2:])

    chain.extend(chain_ids(nxt))

    return chain


def layer_ids_list(chain_ids_list: list, config_image: dict) -> list[str]:
    config_image.pop("id", "")

    chan_ids = []
    parent = None
    for chain_id in chain_ids_list:
        config = LayerConfig(layer_id=chain_id, parent=parent)

        config.container_config = ContainerConfig()
        if chain_id == chain_ids_list[-1]:
            config.config = ContainerConfig()
            config.deepcopy(config_image)

        parent = "sha256:" + hashlib.sha256(config.json.encode()).hexdigest()
        chan_ids.append(parent)

    return chan_ids



class ImageParser:
    REGISTRY_HOST = "registry-1.docker.io"
    REGISTRY_IMAGE_PREFIX = "library"
    DEFAULT_IMAGE_TAG = "latest"

    def __init__(self, image: str):
        self._registry = None
        self._image = None
        self._tag = None
        self._digest = None
        self._manifest_digest = None

        self._from_string(image)

    def __str__(self):
        return f"{self.registry}/{self.image}:{self.image_digest or self.tag}"

    def _from_string(self, image: str):
        registry = self.REGISTRY_HOST
        tag = self.DEFAULT_IMAGE_TAG

        idx = image.find("/")
        if idx > -1 and ("." in image[:idx] or ":" in image[:idx]):
            registry = image[:idx]
            image = image[idx + 1 :]

        idx = image.find("@")
        if idx > -1:
            self._manifest_digest = tag = image[idx + 1 :]
            image = image[:idx]

        idx = image.find(":")
        if idx > -1:
            tag = image[idx + 1 :]
            image = image[:idx]

        self._registry = registry
        self._image = image
        if not self._manifest_digest:
            self._tag = tag

    def _url(self, typ: str, tag: str):
        img = self.image
        idx = img.find("/")
        if idx == -1 and self.registry == self.REGISTRY_HOST:
            img = path_join(self.REGISTRY_IMAGE_PREFIX, img)

        return f"{self._registry}/v2/{img}/{typ}/{tag}"

    @property
    def url_manifests(self):
        return self._url("manifests", self._manifest_digest or self._tag)

    @property
    def url_config_image(self):
        return self.url_blobs(self._digest or self._tag)

    def url_blobs(self, layer_digest: str):
        return self._url("blobs", layer_digest)

    @property
    def image_digest(self):
        return self._digest

    @property
    def manifest_digest(self):
        return self._manifest_digest

    @property
    def image(self):
        return self._image

    @property
    def registry(self):
        return self._registry

    @property
    def tag(self):
        return self._tag

    def set_manifest_digest(self, dig: str):
        self._manifest_digest = dig

    def set_image_digest(self, dig: str):
        self._digest = dig


class ImageFetcher:
    __LST_MTYPE = "application/vnd.docker.distribution.manifest.list.v2+json"
    __IMG_MANIFEST_FORMAT = "application/vnd.docker.distribution.manifest.v2+json"
    __OCI_IMAGE_MANIFEST_FORMAT = "application/vnd.oci.image.manifest.v1+json"
    __OCI_IMAGE_INDEX_FORMAT = "application/vnd.oci.image.index.v1+json"

    def __init__(
        self,
        work_dir: Path,
        *,
        progress: ProgressBar = EmptyProgressBar(),
        save_cache: bool = False,
    ):

        self.__registry_list: dict[str, Registry] = {}
        self._fsm = FilesManager(work_dir)
        self._save_cache = save_cache
        self.__progress_bar = progress

    def set_registry(
        self,
        registry: str,
        user: str = None,
        password: str = None,
        ssl: bool = True,
    ):
        registry = registry.lstrip("https://").lstrip("http://")

        creds = requests.auth.HTTPBasicAuth(user, password) if user else None
        self.__registry_list[registry] = Registry(creds, ssl)

    def _get_registry(self, registry: str) -> Registry:
        return self.__registry_list.get(registry, Registry())

    def _fetch_image(self, img: ImageParser, media_type: str, dir_name: str):
        registry = self._get_registry(img.registry)
        saver = self._fsm(dir_name)

        # get image manifest
        image_manifest_resp = registry.get(
            img.url_manifests, headers={"Accept": media_type}
        )
        image_manifest_spec = image_manifest_resp.json()

        if image_manifest_spec["schemaVersion"] == 1:
            raise ValueError("schema version 1 image manifest not supported")

        img.set_image_digest(image_manifest_spec["config"]["digest"])

        # get image config
        image_config_resp = registry.get(img.url_config_image)
        image_config = image_config_resp.json(cls=JSONDecoderRawString)

        # save image config
        image_digest_hash = img.image_digest.split(":")[1]
        image_config_filename = f"{image_digest_hash}.json"
        saver.write(image_config_filename, image_config_resp.content)

        image_manifest = Manifest(Config=image_config_filename)
        if img.tag:
            image_manifest.RepoTags.append(f"{img.image}:{img.tag}")
        else:
            image_manifest.RepoTags = None

        # fetch all layers with metadata
        diff_ids = image_config["rootfs"]["diff_ids"]
        chain_ids_list = chain_ids(diff_ids)
        v1_layer_ids_list = layer_ids_list(chain_ids_list, image_config)

        v1_layer_id = None
        parent_id = None
        previous_digest = None
        layers = image_manifest_spec["layers"]
        for i, layer_info in enumerate(layers):
            v1_layer_id = v1_layer_ids_list[i][7:]
            image_manifest.Layers.append(f"{v1_layer_id}/layer.tar")

            v1_layer_info = V1Image(
                id=v1_layer_id,
                parent=parent_id,
                os=image_config["os"],
                container_config=ContainerConfig(),
            )

            if layer_info == layers[-1]:
                v1_layer_info.config = ContainerConfig()
                v1_layer_info.deepcopy(image_config)

            digest = layer_info["digest"]
            with saver(v1_layer_id) as fw:
                if previous_digest == digest:
                    # `docker save` command is not deterministic https://github.com/moby/moby/issues/42766#issuecomment-1801221610
                    os.symlink(
                        f"../{parent_id}/layer.tar", fw.filepath("layer.tar")
                    )
                else:
                    registry.fetch_blob(
                        img.url_blobs(digest),
                        fw.filepath("layer.tar"),
                        headers={"Accept": layer_info["mediaType"]},
                        progress=self.__progress_bar,
                    )

                fw.write("json", v1_layer_info.json)
                fw.write("VERSION", "1.0")

            previous_digest = digest
            parent_id = v1_layer_id

        if img.tag:
            # https://github.com/moby/moby/issues/45440
            # docker didn't create this file when pulling image by digest,
            # but podman created ¯\_(ツ)_/¯
            repos_legacy = {img.image: {img.tag: v1_layer_id}}
            data = json.dumps(repos_legacy, separators=JSON_SEPARATOR) + "\n"

            saver.write("repositories", data)

        images_manifest_list = ManifestList()
        images_manifest_list.manifests.append(image_manifest)
        saver.write("manifest.json", images_manifest_list.json + "\n")

        # Save layers with metadata to tar file
        filename = str(self._fsm.work_dir.joinpath(dir_name)) + ".tar"
        created = date_parse(image_config["created"]).timestamp()

        make_tar(Path(filename), saver.work_dir, created)
        os.chmod(filename, 0o600)
        if not self._save_cache:
            shutil.rmtree(saver.work_dir)

    def pull(self, image: str, platform: str):
        img = ImageParser(image)
        registry = self._get_registry(img.registry)

        print(f"{img.tag}: Pulling from {img.image}")
        # get manifest list
        headers = {"Accept": self.__LST_MTYPE}
        manifest_resp = registry.get(img.url_manifests, headers=headers)
        manifest = manifest_resp.json()

        if not img.manifest_digest:
            if manifest["mediaType"] == self.__IMG_MANIFEST_FORMAT or \
                    manifest["mediaType"] == self.__OCI_IMAGE_MANIFEST_FORMAT:
                self._pull_from_manifest(img, manifest)
            elif manifest["mediaType"] == self.__LST_MTYPE or \
                    manifest["mediaType"] == self.__OCI_IMAGE_INDEX_FORMAT:
                self._pull_from_mainfest_list(img, manifest, platform)
        else:
            img_name_n = img.image.replace("/", "_")
            img_tag_n = img.manifest_digest.replace(":", "_").replace(
                "@", "_"
            )
            img_os, img_arch = image_platform(platform)
            dir_name = f"{img_name_n}_{img_tag_n}_{img_os}_{img_arch}"

            self._fetch_image(img, manifest["mediaType"], dir_name)

        print("Digest:", img.image_digest, "\n")

    def _manifests(self, manifest: dict, platform: str) -> list:
        if manifest.get("schemaVersion") == 1:
            raise ValueError("schema version 1 image manifest not supported")
        img_os, img_arch = image_platform(platform)
        print(f"Platform: {img_os}/{img_arch}")
        manifests = manifest.get("manifests", [])

        if not img_os and not img_arch:
            return manifests

        out = []
        for mfst in manifests:
            plf = mfst["platform"]

            if img_os and img_arch:
                if plf["os"] == img_os and plf["architecture"] == img_arch:
                    out.append(mfst)
                    break
            else:
                if plf["os"] == img_os or plf["architecture"] == img_arch:
                    out.append(mfst)

        return out
    
    def _pull_from_manifest(self, img: ImageParser, manifest: dict):
        img_name_n = img.image.replace("/", "_")
        img_tag_n = img.tag.replace(":", "_")
        dir_name = f"{img_name_n}_{img_tag_n}"

        self._fetch_image(img, manifest["mediaType"], dir_name)


    def _pull_from_mainfest_list(self, img: ImageParser, manifest: dict, platform: str):
        for mfst in self._manifests(manifest, platform):
            img.set_manifest_digest(mfst["digest"])
            img_name_n = img.image.replace("/", "_")
            img_tag_n = img.tag.replace(":", "_")
            plf = mfst["platform"]
            arch = plf["architecture"]
            dir_name = f"{img_name_n}_{img_tag_n}_{plf['os']}_{arch}"

            self._fetch_image(img, mfst["mediaType"], dir_name)
import dataclasses
import json
from json_util import JSON_SEPARATOR, StructClassesJSONEncoder

@dataclasses.dataclass
class StructClasses:
    @property
    def json(self) -> str:
        j = json.dumps(
            self, cls=StructClassesJSONEncoder, separators=JSON_SEPARATOR
        )

        return j.replace(r"\\u", r"\u")

    def _update(self, o, kwargs):
        for k, v in kwargs.items():
            if hasattr(o, k):
                _o = getattr(o, k)
                if dataclasses.is_dataclass(_o):
                    _v = type(_o)()
                    self._update(_v, v)
                    v = _v

                setattr(o, k, v)

    def deepcopy(self, kwargs):
        self._update(self, kwargs)


@dataclasses.dataclass
class HealthConfig(StructClasses):
    Test: list[str] = dataclasses.field(
        default_factory=list, metadata={"omitempty": True}
    )
    Interval: str = dataclasses.field(
        default="", metadata={"omitempty": True}
    )
    Timeout: str = dataclasses.field(default="", metadata={"omitempty": True})
    StartPeriod: str = dataclasses.field(
        default="", metadata={"omitempty": True}
    )
    Retries: int = dataclasses.field(default=0, metadata={"omitempty": True})


@dataclasses.dataclass
class ContainerConfig(StructClasses):
    Hostname: str = dataclasses.field(default="")
    Domainname: str = dataclasses.field(default="")
    User: str = dataclasses.field(default="")
    AttachStdin: bool = dataclasses.field(default=False)
    AttachStdout: bool = dataclasses.field(default=False)
    AttachStderr: bool = dataclasses.field(default=False)
    ExposedPorts: dict = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    Tty: bool = dataclasses.field(default=False)
    OpenStdin: bool = dataclasses.field(default=False)
    StdinOnce: bool = dataclasses.field(default=False)
    Env: list = dataclasses.field(default=None)
    Cmd: list = dataclasses.field(default=None)
    Healthcheck: HealthConfig = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    ArgsEscaped: bool = dataclasses.field(
        default=False, metadata={"omitempty": True}
    )
    Image: str = dataclasses.field(default="")
    Volumes: dict = dataclasses.field(default=None)
    WorkingDir: str = dataclasses.field(default="")
    Entrypoint: list = dataclasses.field(default=None)
    NetworkDisabled: bool = dataclasses.field(
        default=False, metadata={"omitempty": True}
    )
    MacAddress: str = dataclasses.field(
        default="", metadata={"omitempty": True}
    )
    OnBuild: list = dataclasses.field(default=None)
    Labels: dict = dataclasses.field(default=None)
    StopSignal: str = dataclasses.field(
        default="", metadata={"omitempty": True}
    )
    StopTimeout: int = dataclasses.field(
        default=0, metadata={"omitempty": True}
    )
    Shell: list = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )


@dataclasses.dataclass
class LayerConfig(StructClasses):
    architecture: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    comment: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    config: ContainerConfig = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    container: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    container_config: ContainerConfig = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    created: str = dataclasses.field(default="1970-01-01T00:00:00Z")
    docker_version: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    layer_id: str = dataclasses.field(default="")
    os: str = dataclasses.field(default=None, metadata={"omitempty": True})
    parent: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    variant: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )


@dataclasses.dataclass
class V1Image(StructClasses):
    id: str = dataclasses.field(default=None, metadata={"omitempty": True})
    parent: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    comment: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    created: str = "1970-01-01T00:00:00Z"
    container: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    container_config: ContainerConfig = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    docker_version: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    author: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    config: ContainerConfig = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    architecture: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    variant: str = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    os: str = dataclasses.field(default="linux", metadata={"omitempty": True})
    size: int = dataclasses.field(default=None, metadata={"omitempty": True})


@dataclasses.dataclass
class RootFS:
    type: str
    diff_ids: list[str] = dataclasses.field(
        default_factory=list, metadata={"omitempty": True}
    )


@dataclasses.dataclass
class Image(V1Image):
    rootfs: RootFS = dataclasses.field(
        default=None, metadata={"omitempty": True}
    )
    history: list[str] = dataclasses.field(
        default_factory=list, metadata={"omitempty": True}
    )


@dataclasses.dataclass
class Manifest:
    Config: str = ""
    RepoTags: list[str] = dataclasses.field(default_factory=list)
    Layers: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ManifestList:
    manifests: list[Manifest] = dataclasses.field(default_factory=list)

    @property
    def json(self) -> str:
        r = []
        for m in self.manifests:
            r.append(dataclasses.asdict(m))

        return json.dumps(r, separators=JSON_SEPARATOR, ensure_ascii=False)

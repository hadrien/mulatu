from __future__ import annotations

import re

from dataclasses import dataclass, field
from fastapi.openapi import models
from slugify import slugify
from structlog import get_logger
from typing import Callable, Dict, List, Optional, cast


log = get_logger(__name__)


def new(spec: models.OpenAPI) -> Resource:
    root_path_item: models.PathItem = spec.paths.get("/", models.PathItem())
    root: Resource = Root(parent=None, path="/", path_item=root_path_item)

    # ["/pet/{petId}", "/pet/inventory"] -> [["pet", "{petId}"], ["store", "inventory"]]
    path_elements = [filter(None, p.split("/")) for p in sorted(spec.paths.keys())]
    for resource_names in path_elements:
        parent = root
        path = ""
        for name in resource_names:
            path += f"/{name}"
            path_item = spec.paths.get(path)
            resource = (
                parent.resources[path]
                if path in parent.resources
                else parent.add_resource(parent, path, path_item)
            )
            parent = resource
    return root


@dataclass
class Method:
    verb: str
    resource: Resource = field(repr=False)
    operation: models.Operation = field(repr=False)


@dataclass
class Resource:
    parent: Optional[Resource] = field(repr=False)
    path: str
    path_item: Optional[models.PathItem] = field(repr=False)
    resources: Dict[str, Resource] = field(
        init=False, default_factory=lambda: {}, repr=False
    )
    methods: Dict[str, Method] = field(
        init=False, default_factory=lambda: {}, repr=False
    )

    @property
    def name(self) -> str:
        return self.path.rsplit("/", maxsplit=1).pop()

    @property
    def safe_name(self) -> str:
        return cast(str, slugify(self.name, separator="_"))

    @property
    def class_name(self):
        parent_class_name = (
            self.parent.class_name if not isinstance(self.parent, Root) else ""
        )
        if self.is_pattern():
            return f"{parent_class_name}Item"
        else:
            value = "".join(part.title() for part in self.name.split("-"))
            return f"{parent_class_name}{value}"

    @property
    def pattern_child(self) -> Resource:
        return next(
            resource for resource in self.resources.values() if resource.is_pattern()
        )

    @property
    def all_resources(self) -> List[Resource]:
        result: List[Resource] = []
        self.walk(result.append)
        return result

    def walk(self, on_resource: Callable[[Resource], None]):
        on_resource(self)
        for resource in self.resources.values():
            resource.walk(on_resource)

    def is_pattern(self) -> bool:
        return bool(re.match("{.*}", self.name))

    def has_pattern_child(self) -> bool:
        return any([resource.is_pattern() for resource in self.resources.values()])

    def add_resource(
        self, parent: Resource, path: str, path_item: Optional[models.PathItem]
    ) -> Resource:
        resource = Resource(parent, path, path_item)
        self.resources[path] = resource
        log.debug("add resource", resource=resource)
        if path_item:
            for verb in "delete get patch post put".split():
                operation: models.Operation = getattr(path_item, verb)
                if operation is None:
                    continue
                resource.add_method(verb, operation)
        return resource

    def add_method(self, verb: str, operation: models.Operation) -> Method:
        method = Method(self, verb, operation)
        self.methods[verb] = operation
        log.debug(
            "new http method",
            verb=verb,
            operation_id=operation.operationId,
            method=method,
        )
        return method


class Root(Resource):
    @property
    def class_name(self):
        return "Root"

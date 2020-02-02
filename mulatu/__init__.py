from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
from argparse import ArgumentParser, FileType
from dataclasses import dataclass, field
from typing import Dict, List, Optional, cast

import pkg_resources
from fastapi.openapi import models
from mako.template import Template
from prance import BaseParser as OpenAPIParser
from structlog import get_logger
from slugify import slugify

log = get_logger(__name__)


def new_args_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate Open API client.")
    parser.add_argument(
        "--spec",
        dest="openapi_spec_stream",
        type=FileType("r"),
        default="-",
        help="Open API spec file to generate client from. Default to stdin",
    )
    parser.add_argument("package_name", help="Generated package name")
    return parser


def run(argv: List[str]):
    parser = new_args_parser()
    namespace = parser.parse_args(argv)
    spec = parse_openapi_spec(namespace.openapi_spec_stream)
    root = new_tree(spec)
    generate_project(namespace.package_name, root)


def main():
    argv = sys.argv[1:]
    run(argv)


def parse_openapi_spec(openapi_spec_stream: io.TextIOBase) -> models.OpenAPI:
    spec_string = openapi_spec_stream.read()
    parser = OpenAPIParser(spec_string=spec_string)
    spec = models.OpenAPI(**parser.specification)
    return spec


@dataclass
class Operation:
    doc: str = field(repr=False)
    verb: str


@dataclass
class Resource:
    parent: Optional[Resource] = field(repr=False)
    path: str
    path_item: Optional[models.PathItem] = field(repr=False)
    resources: Dict[str, Resource] = field(
        init=False, default_factory=lambda: {}, repr=False
    )
    operations: Dict[str, Operation] = field(
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
                op: models.Operation = getattr(path_item, verb)
                if op is None:
                    continue
                resource.add_operation(op, verb)
        return resource

    def add_operation(self, op: models.Operation, verb: str) -> Operation:
        description: str = op.description or ""
        operation = Operation(description, verb)
        self.operations[verb] = operation
        log.debug(
            "new operation", verb=verb, operation_id=op.operationId, operation=operation
        )
        return operation


class Root(Resource):
    @property
    def class_name(self):
        return "Root"


def new_tree(spec: models.OpenAPI) -> Resource:
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


def generate_project(package_name: str, root: Resource) -> str:
    tpl_dir = pkg_resources.resource_filename("mulatu", f"templates")
    out_dir = tempfile.mkdtemp(prefix="mulatu-")
    pkg_dir = os.path.join(out_dir, package_name)
    os.mkdir(pkg_dir)

    for dirpath, dirnames, filenames in os.walk(tpl_dir):
        for filename in filenames:
            module_path = os.path.join(pkg_dir, filename.strip(".mako"))
            tpl_path = os.path.join(dirpath, filename)
            template = Template(filename=tpl_path)
            with open(module_path, "w") as fd:
                fd.write(template.render(package_name=package_name, root=root))
                log.debug("module generated", module_path=module_path)

    subprocess.run(["black", "-q", out_dir])

    log.debug("project generated", directory=f"file://{out_dir}")
    return out_dir

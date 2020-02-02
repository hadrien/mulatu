from __future__ import annotations

import io
import sys
from argparse import ArgumentParser, FileType
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from fastapi.openapi import models
from prance import BaseParser as OpenAPIParser
from structlog import get_logger

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
    root.walk(print_resource)


def print_resource(node: Resource):
    log.debug("walking", node=node)


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
    path: str
    path_item: Optional[models.PathItem] = field(repr=False)
    resources: Dict[str, Resource] = field(
        init=False, default_factory=lambda: {}, repr=False
    )
    operations: Dict[str, Operation] = field(
        init=False, default_factory=lambda: {}, repr=False
    )

    def add_resource(self, path: str, path_item: Optional[models.PathItem]) -> Resource:
        resource = Resource(path=path, path_item=path_item)
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

    def walk(self, on_resource: Callable[[Resource], None]):
        on_resource(self)
        for resource in self.resources.values():
            resource.walk(on_resource)


class Root(Resource):
    pass


def new_tree(spec: models.OpenAPI) -> Resource:
    root_path_item: models.PathItem = spec.paths.get("/", models.PathItem())
    root: Resource = Root("/", root_path_item)

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
                else parent.add_resource(path, path_item)
            )
            parent = resource
    return root


def main():
    argv = sys.argv[1:]
    run(argv)

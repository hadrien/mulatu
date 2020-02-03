from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
from argparse import ArgumentParser, FileType
from typing import List

import pkg_resources
from fastapi.openapi import models
from mako.template import Template
from prance import BaseParser as OpenAPIParser
from structlog import get_logger

from . import tree

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
    root = tree.new(spec)
    generate_project(namespace.package_name, root)


def main():
    argv = sys.argv[1:]
    run(argv)


def parse_openapi_spec(openapi_spec_stream: io.TextIOBase) -> models.OpenAPI:
    spec_string = openapi_spec_stream.read()
    parser = OpenAPIParser(spec_string=spec_string)
    spec = models.OpenAPI(**parser.specification)
    return spec


def generate_project(package_name: str, root: tree.Root) -> str:
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

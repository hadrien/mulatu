import io
import sys
from argparse import ArgumentParser, FileType
from typing import List

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
    parse_openapi_spec(namespace.openapi_spec_stream)


def parse_openapi_spec(openapi_spec_stream: io.TextIOBase) -> models.OpenAPI:
    spec_string = openapi_spec_stream.read()
    parser = OpenAPIParser(spec_string=spec_string)
    spec = models.OpenAPI(**parser.specification)
    return spec


def main():
    argv = sys.argv[1:]
    run(argv)

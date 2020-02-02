from pytest import fixture


@fixture
def args_parser():
    from mulatu import new_args_parser

    return new_args_parser()


def test_parse_args_with_spec_from_stdin(args_parser, petstore_stdin):
    args_parser.parse_args(["petstore"])


def test_parse_args_with_spec_from_file(args_parser):
    args_parser.parse_args("--spec tests/petstore.yaml petstore".split())

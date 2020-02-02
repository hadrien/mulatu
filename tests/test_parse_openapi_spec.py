def test_parse_openapi_spec(petstore_spec_stdin):
    from mulatu import parse_openapi_spec

    parse_openapi_spec(petstore_spec_stdin)

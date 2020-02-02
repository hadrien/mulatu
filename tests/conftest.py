from pytest import fixture


@fixture
def petstore_stdin(monkeypatch):
    with open("tests/petstore.yaml", "r") as f:
        monkeypatch.setattr("sys.stdin", f)
        yield f

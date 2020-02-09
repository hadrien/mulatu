import subprocess

from pytest import fixture


@fixture
def sys_argv(monkeypatch):
    argv = "mulatu petstore".split()
    monkeypatch.setattr("sys.argv", argv)
    yield argv


def test_main(sys_argv, petstore_spec_stdin):
    from mulatu import main

    main()


def test_command_line():
    subprocess.run(["mulatu", "-h"])

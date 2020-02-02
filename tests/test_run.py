import subprocess

from pytest import fixture


@fixture
def sys_argv(monkeypatch):
    argv = "mulatu petstore".split()
    monkeypatch.setattr("sys.argv", argv)
    yield argv


def test_run(petstore_stdin):
    from mulatu import run

    run(["petstore"])


def test_main(sys_argv, petstore_stdin):
    from mulatu import main

    main()


def test_command_line(sys_argv, petstore_stdin):
    subprocess.run(["mulatu", "petstore"])

import os
import shutil
import subprocess

import nox

SOURCE_FILES = [
    "docs/",
    "dummyserver/",
    "src/",
    "test/",
    "noxfile.py",
    "setup.py",
]


def tests_impl(session, extras="socks,secure,brotli"):
    # Install deps and the package itself.
    session.install("-r", "dev-requirements.txt")
    session.install(f".[{extras}]")

    # Show the pip version.
    session.run("pip", "--version")
    # Print the Python version and bytesize.
    session.run("python", "--version")
    session.run("python", "-c", "import struct; print(struct.calcsize('P') * 8)")
    # Print OpenSSL information.
    session.run("python", "-m", "OpenSSL.debug")

    # Inspired from https://github.com/pyca/cryptography
    # We use parallel mode and then combine here so that coverage.py will take
    # the paths like .tox/pyXY/lib/pythonX.Y/site-packages/urllib3/__init__.py
    # and collapse them into src/urllib3/__init__.py.

    session.run(
        "coverage",
        "run",
        "--parallel-mode",
        "-m",
        "pytest",
        "-r",
        "a",
        "--tb=native",
        "--no-success-flaky-report",
        *(session.posargs or ("test/",)),
        env={"PYTHONWARNINGS": "always::DeprecationWarning"},
    )
    session.run("coverage", "combine")
    session.run("coverage", "report", "-m")
    session.run("coverage", "xml")


@nox.session(python=["3.6", "3.7", "3.8", "3.9", "3.10", "pypy"])
def test(session):
    tests_impl(session)


@nox.session(python=["2.7"])
def unsupported_python2(session):
    # Can't check both returncode and output with session.run
    process = subprocess.run(
        ["python", "setup.py", "install"],
        env={**session.env},
        text=True,
        capture_output=True,
    )
    assert process.returncode == 1
    print(process.stderr)
    assert "Unsupported Python version" in process.stderr


@nox.session(python=["3"])
def test_brotlipy(session):
    """Check that if 'brotlipy' is installed instead of 'brotli' or
    'brotlicffi' that we still don't blow up.
    """
    session.install("brotlipy")
    tests_impl(session, extras="socks,secure")


@nox.session()
def format(session):
    """Run code formatters."""
    session.install("pre-commit")
    session.run("pre-commit", "--version")

    process = subprocess.run(
        ["pre-commit", "run", "--all-files"],
        env=session.env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Ensure that pre-commit itself ran successfully
    assert process.returncode in (0, 1)

    lint(session)


@nox.session
def lint(session):
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")

    mypy(session)


@nox.session(python="3.8")
def mypy(session):
    """Run mypy."""
    session.install("mypy==0.910")
    session.install("idna>=2.0.0")
    session.install("cryptography>=1.3.4")
    session.run("mypy", "--version")
    session.run("mypy", "--strict", "src/urllib3")


@nox.session
def docs(session):
    session.install("-r", "docs/requirements.txt")
    session.install(".[socks,secure,brotli]")

    session.chdir("docs")
    if os.path.exists("_build"):
        shutil.rmtree("_build")
    session.run("sphinx-build", "-b", "html", "-W", ".", "_build/html")

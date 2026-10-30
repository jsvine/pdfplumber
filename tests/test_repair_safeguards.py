"""Regression tests for the pdfplumber repair.py safeguards.

Every safeguard test FAILS against stock pdfplumber 0.11.10 and PASSES
against the patched tree. Stub Ghostscript binaries (shell scripts) stand in
for a real `gs`: one records its argv and emits fixed output, one sleeps so
the timeout -- and the kill that must accompany it -- can be observed.

Run against stock:   pytest test_pdfplumber_repair.py
Run against patched: PYTHONPATH=<patched tree root> pytest test_pdfplumber_repair.py
"""

import importlib
import os
import stat
import subprocess
import time
from io import BytesIO

import pytest

# pdfplumber/__init__.py re-exports the repair() function under the same
# name as the submodule, so import the module object explicitly.
repair_mod = importlib.import_module("pdfplumber.repair")


def _write_stub(tmp_path, name, body):
    stub = tmp_path / name
    stub.write_text(body)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return str(stub)


@pytest.fixture()
def argv_stub(tmp_path, monkeypatch):
    """A gs stub that logs its argv to $GS_STUB_ARGV_LOG and emits bytes."""
    log = tmp_path / "argv.log"
    monkeypatch.setenv("GS_STUB_ARGV_LOG", str(log))
    stub = _write_stub(
        tmp_path,
        "gs-argv",
        '#!/bin/sh\necho "$@" >> "$GS_STUB_ARGV_LOG"\nprintf "repaired-bytes"\n',
    )
    return stub, log


def test_repair_passes_safer_and_batch_flags(argv_stub):
    stub, log = argv_stub
    out = repair_mod.repair(BytesIO(b"%PDF-fake"), gs_path=stub)
    assert out is not None and out.read() == b"repaired-bytes"
    argv = log.read_text()
    for flag in ("-dSAFER", "-dNOPAUSE", "-dBATCH"):
        assert flag in argv, f"{flag} missing from Ghostscript argv: {argv}"


def test_repair_control_without_timeout_kwarg_still_works(argv_stub):
    stub, _ = argv_stub
    out = repair_mod.repair(BytesIO(b"%PDF-fake"), gs_path=stub)
    assert out is not None and out.read() == b"repaired-bytes"


@pytest.fixture()
def sleep_stub(tmp_path, monkeypatch):
    """A gs stub that records its PID, then replaces itself with `sleep`.

    Because of `exec`, the recorded PID *is* the long-running process, so the
    test can verify the timeout path actually kills it.
    """
    pidfile = tmp_path / "gs.pid"
    monkeypatch.setenv("GS_STUB_PIDFILE", str(pidfile))
    stub = _write_stub(
        tmp_path,
        "gs-sleep",
        '#!/bin/sh\necho $$ > "$GS_STUB_PIDFILE"\nexec sleep 60\n',
    )
    return stub, pidfile


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_public_repair_forwards_timeout_and_kills_ghostscript(sleep_stub):
    stub, pidfile = sleep_stub
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        repair_mod.repair(BytesIO(b"%PDF-fake"), gs_path=stub, timeout=0.5)
    elapsed = time.monotonic() - start
    assert elapsed < 20, f"timeout did not fire promptly ({elapsed:.1f}s)"
    pid = int(pidfile.read_text().strip())
    # Give the killed process a moment to be reaped, then require it gone.
    for _ in range(50):
        if not _pid_alive(pid):
            break
        time.sleep(0.1)
    assert not _pid_alive(pid), "Ghostscript stub was not killed on timeout"


def test_private_repair_timeout_parameter(sleep_stub):
    stub, _ = sleep_stub
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        repair_mod._repair(BytesIO(b"%PDF-fake"), gs_path=stub, timeout=0.5)
    assert time.monotonic() - start < 20


def test_repair_timeout_default_is_finite():
    import inspect

    for fn in (repair_mod.repair, repair_mod._repair):
        default = inspect.signature(fn).parameters["timeout"].default
        assert default is not None and default > 0

import pathlib
import shutil
import subprocess
from io import BufferedReader, BytesIO
from typing import Literal, Optional, Union

T_repair_setting = Literal["default", "prepress", "printer", "ebook", "screen"]

# Upper bound for a single Ghostscript repair run. Repairs of well-formed
# PDFs normally finish in seconds; the timeout exists so a damaged or
# hostile PDF cannot make Ghostscript run forever. Pass timeout=None to
# disable it.
DEFAULT_TIMEOUT: Optional[float] = 60.0


def _repair(
    path_or_fp: Union[str, pathlib.Path, BufferedReader, BytesIO],
    password: Optional[str] = None,
    gs_path: Optional[Union[str, pathlib.Path]] = None,
    setting: T_repair_setting = "default",
    timeout: Optional[float] = DEFAULT_TIMEOUT,
) -> BytesIO:

    executable = (
        gs_path
        or shutil.which("gs")
        or shutil.which("gswin32c")
        or shutil.which("gswin64c")
    )
    if executable is None:  # pragma: nocover
        raise Exception(
            "Cannot find Ghostscript, which is required for repairs.\n"
            "Visit https://www.ghostscript.com/ for installation instructions."
        )

    repair_args = [
        executable,
        # -dSAFER confines Ghostscript's file access to the job's own
        # inputs/outputs; without it, a PDF under repair can direct
        # Ghostscript to read or write arbitrary files via PostScript
        # operators. -dNOPAUSE/-dBATCH make the non-interactive contract
        # explicit (the "-o -" below already implies it on modern
        # Ghostscript, but the flags keep older builds honest).
        "-dSAFER",
        "-dNOPAUSE",
        "-dBATCH",
        "-sstdout=%stderr",
        "-o",
        "-",
        "-sDEVICE=pdfwrite",
        f"-dPDFSETTINGS=/{setting}",
    ]

    if password:
        repair_args += [f"-sPDFPassword={password}"]

    if isinstance(path_or_fp, (str, pathlib.Path)):
        stdin = None
        repair_args += [str(pathlib.Path(path_or_fp).absolute())]
    else:
        stdin = path_or_fp
        repair_args += ["-"]

    proc = subprocess.Popen(
        repair_args,
        stdin=subprocess.PIPE if stdin else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        stdout, stderr = proc.communicate(
            stdin.read() if stdin else None, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        # communicate() alone does not stop the child; kill it and reap it
        # before surfacing the timeout, so no Ghostscript process is left
        # running against the caller's input.
        proc.kill()
        proc.communicate()
        raise

    if proc.returncode:
        raise Exception(f"{stderr.decode('utf-8')}")

    return BytesIO(stdout)


def repair(
    path_or_fp: Union[str, pathlib.Path, BufferedReader, BytesIO],
    outfile: Optional[Union[str, pathlib.Path]] = None,
    password: Optional[str] = None,
    gs_path: Optional[Union[str, pathlib.Path]] = None,
    setting: T_repair_setting = "default",
    timeout: Optional[float] = DEFAULT_TIMEOUT,
) -> Optional[BytesIO]:
    repaired = _repair(
        path_or_fp, password, gs_path=gs_path, setting=setting, timeout=timeout
    )
    if outfile:
        with open(outfile, "wb") as f:
            f.write(repaired.read())
        return None
    else:
        return repaired

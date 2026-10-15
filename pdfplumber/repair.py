import pathlib
import shutil
import subprocess
from io import BufferedReader, BytesIO
from typing import Literal, Optional, Union

T_repair_setting = Literal["default", "prepress", "printer", "ebook", "screen"]


def _repair(
    path_or_fp: Union[str, pathlib.Path, BufferedReader, BytesIO],
    password: Optional[str] = None,
    gs_path: Optional[Union[str, pathlib.Path]] = None,
    setting: T_repair_setting = "default",
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
        # Ghostscript processes the (untrusted) input document here, so run it
        # under its `-dSAFER` sandbox. SAFER is only the default on Ghostscript
        # >= 9.50; older builds (still shipped by several long-term-support
        # distributions) leave it off, letting a crafted PDF reach the
        # file/pipe operators. Passing it explicitly enforces the sandbox
        # regardless of the installed Ghostscript's default.
        "-dSAFER",
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

    stdout, stderr = proc.communicate(stdin.read() if stdin else None)

    if proc.returncode:
        raise Exception(f"{stderr.decode('utf-8')}")

    return BytesIO(stdout)


def repair(
    path_or_fp: Union[str, pathlib.Path, BufferedReader, BytesIO],
    outfile: Optional[Union[str, pathlib.Path]] = None,
    password: Optional[str] = None,
    gs_path: Optional[Union[str, pathlib.Path]] = None,
    setting: T_repair_setting = "default",
) -> Optional[BytesIO]:
    repaired = _repair(path_or_fp, password, gs_path=gs_path, setting=setting)
    if outfile:
        with open(outfile, "wb") as f:
            f.write(repaired.read())
        return None
    else:
        return repaired

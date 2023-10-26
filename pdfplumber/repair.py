import pathlib
import shutil
import subprocess
from io import BufferedReader, BytesIO
from typing import Optional, Union


def _repair(
    path_or_fp: Union[str, pathlib.Path, BufferedReader, BytesIO],
    password: Optional[str] = None,
    gs_path: Optional[Union[str, pathlib.Path]] = None,
) -> BytesIO:

    executable = gs_path or shutil.which("gs") or shutil.which("gswin32c")
    if executable is None:  # pragma: nocover
        raise Exception(
            "Cannot find Ghostscript, which is required for repairs.\n"
            "Visit https://www.ghostscript.com/ for installation instructions."
        )

    repair_args = [
        executable,
        "-o",
        "-",
        "-sDEVICE=pdfwrite",
        "-dPDFSETTINGS=/prepress",
    ]

    if password:
        repair_args += [f"-sPDFPassword={password}"]

    if isinstance(path_or_fp, (str, pathlib.Path)):
        stdin = None
        repair_args += [str(pathlib.Path(path_or_fp).absolute())]
    else:
        stdin = path_or_fp
        repair_args += ["-"]

    stdout, stderr = subprocess.Popen(
        repair_args,
        stdin=subprocess.PIPE if stdin else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate(stdin.read() if stdin else None)

    if len(stderr):
        raise Exception(f"{stderr.decode('utf-8')}")

    return BytesIO(stdout)


def repair(
    path_or_fp: Union[str, pathlib.Path, BufferedReader, BytesIO],
    outfile: Optional[Union[str, pathlib.Path]] = None,
    password: Optional[str] = None,
    gs_path: Optional[Union[str, pathlib.Path]] = None,
) -> Optional[BytesIO]:
    repaired = _repair(path_or_fp, password, gs_path=gs_path)
    if outfile:
        with open(outfile, "wb") as f:
            f.write(repaired.read())
        return None
    else:
        return repaired

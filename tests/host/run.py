"""Compila y prueba el capturador real con GPIO e interrupciones simulados."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "g++"),
                        help="Ejecutable GCC o Clang compatible con C++17")
    parser.add_argument("--expect-failure", action="store_true",
                        help="Inyecta una expectativa incorrecta y devuelve un código distinto de cero")
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent
    source = tests.parents[1] / "src" / "diagnostico"
    try:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "encoder_test.exe"
            subprocess.run([
                args.cxx, "-std=c++17", "-Wall", "-Wextra",
                "-I", str(tests), "-I", str(source),
                str(tests / "encoder_test.cpp"), str(source / "EncoderDiagnostico.cpp"),
                "-o", str(executable),
            ], check=True)
            command = [str(executable)]
            if args.expect_failure:
                command.append("--expect-failure")
            return subprocess.run(command, check=False).returncode
    except FileNotFoundError as error:
        parser.exit(2, f"No se pudo iniciar el compilador o la prueba: {error}\n")
    except subprocess.CalledProcessError as error:
        return error.returncode


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Convertitore STEP → STL
========================
Legge un file STEP (.step / .stp) e lo converte in formato STL.

Utilizzo:
    python step_to_stl.py input.step                  # genera input.stl
    python step_to_stl.py input.step output.stl       # nome output esplicito
    python step_to_stl.py input.step -t 0.5           # tolleranza mesh personalizzata
    python step_to_stl.py input.step --ascii           # formato STL ASCII

Dipendenze:
    pip install cadquery
"""

import argparse
import sys
from pathlib import Path

from OCP.STEPControl import STEPControl_Reader, STEPControl_StepModelType
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.IFSelect import IFSelect_RetDone


def read_step(filepath: str):
    """Legge un file STEP e restituisce la shape OpenCASCADE."""
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Impossibile leggere il file STEP: {filepath}")

    reader.TransferRoots()
    shape = reader.OneShape()
    return shape


def write_stl(shape, filepath: str, tolerance: float = 0.1, ascii_mode: bool = False):
    """Genera la mesh e scrive il file STL."""
    mesh = BRepMesh_IncrementalMesh(shape, tolerance)
    mesh.Perform()
    if not mesh.IsDone():
        raise RuntimeError("Errore durante la generazione della mesh.")

    writer = StlAPI_Writer()
    writer.ASCIIMode = ascii_mode
    success = writer.Write(shape, filepath)
    if not success:
        raise RuntimeError(f"Impossibile scrivere il file STL: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Converte un file STEP (.step/.stp) in formato STL."
    )
    parser.add_argument(
        "input",
        help="Percorso del file STEP di input",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Percorso del file STL di output (default: stesso nome con estensione .stl)",
    )
    parser.add_argument(
        "-t", "--tolerance",
        type=float,
        default=0.1,
        help="Tolleranza della mesh (default: 0.1 — valori più bassi = mesh più fine)",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Salva in formato STL ASCII invece che binario",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Errore: il file '{input_path}' non esiste.", file=sys.stderr)
        sys.exit(1)

    if input_path.suffix.lower() not in (".step", ".stp"):
        print(
            f"Attenzione: il file '{input_path.name}' non ha estensione .step/.stp.",
            file=sys.stderr,
        )

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".stl")

    print(f"Lettura file STEP: {input_path}")
    shape = read_step(str(input_path))

    print(f"Generazione mesh (tolleranza={args.tolerance}) e scrittura STL: {output_path}")
    write_stl(shape, str(output_path), tolerance=args.tolerance, ascii_mode=args.ascii)

    print(f"Conversione completata: {output_path}")


if __name__ == "__main__":
    main()

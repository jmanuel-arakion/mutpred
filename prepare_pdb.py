#!/usr/bin/env python3
"""
prepare_pdb.py

Descarga una estructura del PDB dado su código, extrae un solo modelo
(útil para estructuras NMR) y una cadena específica, y guarda:

  1) archivo original descargado (.pdb o .cif)
  2) cadena extraída como .pdb
  3) secuencia de la cadena en FASTA

Uso:
    python prepare_pdb.py --pdb 1V90 --chain A --outdir data
    python prepare_pdb.py --pdb 1V90 --chain A --model 0 --outdir data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from Bio.PDB import PDBParser, MMCIFParser, PDBIO, Select, is_aa
from Bio.PDB.Polypeptide import protein_letters_3to1

RCSB_PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"
RCSB_CIF_URL = "https://files.rcsb.org/download/{pdb_id}.cif"


def download_file(url: str, dest: Path, timeout: int = 60) -> bool:
    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            if r.status_code != 200:
                return False
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return True
    except requests.RequestException:
        return False


def fetch_structure_file(pdb_id: str, outdir: Path) -> Tuple[Path, str]:
    pdb_id = pdb_id.lower()
    outdir.mkdir(parents=True, exist_ok=True)

    pdb_path = outdir / f"{pdb_id}.pdb"
    cif_path = outdir / f"{pdb_id}.cif"

    if download_file(RCSB_PDB_URL.format(pdb_id=pdb_id), pdb_path):
        return pdb_path, "pdb"

    if download_file(RCSB_CIF_URL.format(pdb_id=pdb_id), cif_path):
        return cif_path, "cif"

    raise RuntimeError(f"No se pudo descargar {pdb_id} ni como .pdb ni como .cif.")


def parse_structure(structure_path: Path, file_format: str, structure_id: str):
    if file_format == "pdb":
        parser = PDBParser(QUIET=True)
    elif file_format == "cif":
        parser = MMCIFParser(QUIET=True)
    else:
        raise ValueError(f"Formato no soportado: {file_format}")
    return parser.get_structure(structure_id, str(structure_path))


def get_model(structure, model_id: Optional[int] = None):
    models = list(structure.get_models())
    if not models:
        raise ValueError("La estructura no contiene modelos.")

    available = [m.id for m in models]

    if model_id is None:
        return models[0], available

    for m in models:
        if m.id == model_id:
            return m, available

    raise ValueError(
        f"El modelo {model_id} no existe. Modelos disponibles: {available}"
    )


def find_chain(model, chain_id: str):
    if chain_id not in model:
        available = [c.id for c in model.get_chains()]
        raise ValueError(
            f"La cadena '{chain_id}' no existe en el modelo seleccionado. "
            f"Cadenas disponibles: {available}"
        )
    return model[chain_id]


class ModelChainSelect(Select):
    def __init__(self, model_id: int, chain_id: str):
        self.model_id = model_id
        self.chain_id = chain_id

    def accept_model(self, model) -> bool:
        return model.id == self.model_id

    def accept_chain(self, chain) -> bool:
        return chain.id == self.chain_id

    def accept_residue(self, residue) -> bool:
        return is_aa(residue, standard=False)

    def accept_atom(self, atom) -> bool:
        altloc = atom.get_altloc()
        return altloc in (" ", "A")


def residue_to_one_letter(residue) -> Optional[str]:
    resname = residue.get_resname().strip().upper()

    aliases = {
        "MSE": "M",
        "SEC": "U",
        "PYL": "O",
    }
    if resname in aliases:
        return aliases[resname]

    try:
        return protein_letters_3to1[resname]
    except KeyError:
        return None


def extract_chain_sequence(chain) -> str:
    seq: List[str] = []
    seen_positions = set()

    for residue in chain.get_residues():
        if not is_aa(residue, standard=False):
            continue

        resid = residue.id
        if resid in seen_positions:
            continue
        seen_positions.add(resid)

        aa = residue_to_one_letter(residue)
        if aa is not None:
            seq.append(aa)

    return "".join(seq)


def save_model_chain_as_pdb(structure, model_id: int, chain_id: str, out_path: Path):
    io = PDBIO()
    io.set_structure(structure)
    io.save(str(out_path), select=ModelChainSelect(model_id, chain_id))


def save_fasta(sequence: str, header: str, out_path: Path, width: int = 80):
    with open(out_path, "w") as f:
        f.write(f">{header}\n")
        for i in range(0, len(sequence), width):
            f.write(sequence[i:i + width] + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga una estructura y extrae un solo modelo y una cadena."
    )
    parser.add_argument("--pdb", required=True, help="Código PDB, por ejemplo 1V90")
    parser.add_argument("--chain", required=True, help="Cadena a extraer, por ejemplo A")
    parser.add_argument(
        "--model",
        type=int,
        default=None,
        help="ID del modelo a usar. Por defecto usa el primero."
    )
    parser.add_argument("--outdir", default="data", help="Directorio de salida")
    parser.add_argument(
        "--prefix",
        default=None,
        help="Prefijo de salida. Por defecto usa <pdb>_<chain>_m<model>"
    )
    args = parser.parse_args()

    pdb_id = args.pdb.strip().lower()
    chain_id = args.chain.strip()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"[1/5] Descargando estructura {pdb_id}...")
        structure_file, fmt = fetch_structure_file(pdb_id, outdir)
        print(f"      OK -> {structure_file.name} ({fmt})")

        print("[2/5] Parseando estructura...")
        structure = parse_structure(structure_file, fmt, pdb_id)

        print("[3/5] Seleccionando modelo...")
        model, available_models = get_model(structure, args.model)
        model_id = model.id
        if len(available_models) > 1:
            print(f"      Estructura con múltiples modelos: {available_models}")
            print(f"      Usando modelo: {model_id}")
        else:
            print(f"      Estructura con un solo modelo: {model_id}")

        print(f"[4/5] Extrayendo cadena {chain_id} del modelo {model_id}...")
        chain = find_chain(model, chain_id)

        prefix = args.prefix or f"{pdb_id}_{chain_id}_m{model_id}"
        chain_pdb_path = outdir / f"{prefix}.chain.pdb"
        fasta_path = outdir / f"{prefix}.fasta"

        save_model_chain_as_pdb(structure, model_id, chain_id, chain_pdb_path)

        sequence = extract_chain_sequence(chain)
        if not sequence:
            raise RuntimeError(
                f"No se pudo extraer secuencia proteica para {pdb_id}, "
                f"modelo {model_id}, cadena {chain_id}."
            )

        save_fasta(sequence, f"{pdb_id}_{chain_id}_model{model_id}", fasta_path)

        print("[5/5] Listo.")
        print(f"      Archivo original : {structure_file}")
        print(f"      Cadena en PDB    : {chain_pdb_path}")
        print(f"      FASTA            : {fasta_path}")
        print(f"      Longitud         : {len(sequence)} aa")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

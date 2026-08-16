"""
Exécute la chaîne complète, du téléchargement aux cartes.

    python run_all.py              chaîne complète
    python run_all.py --depuis 2   reprend à l'étape 2
    python run_all.py --etape 3    n'exécute que l'étape 3

L'étape 2 est la plus longue : l'inférence de Moran repose sur 999 permutations
par année, répétées pour deux définitions du voisinage.
"""

from __future__ import annotations

import argparse
import runpy
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE / "src"))

ETAPES = {
    0: ("Téléchargement des sources", "src/telecharger_donnees.py"),
    1: ("Construction du panel", "src/p01_construire_panel.py"),
    2: ("Dépendance spatiale", "src/p02_dependance_spatiale.py"),
    3: ("Modèles de panel spatiaux", "src/p03_modeles_panel.py"),
    4: ("Cartes et graphiques", "src/p04_cartes.py"),
}


def executer(numero: int) -> None:
    libelle, script = ETAPES[numero]
    print("\n" + "=" * 78)
    print(f"ÉTAPE {numero} — {libelle}")
    print("=" * 78, flush=True)
    debut = time.perf_counter()
    sys.argv = [script]
    runpy.run_path(str(RACINE / script), run_name="__main__")
    print(f"[étape {numero} terminée en {time.perf_counter() - debut:.0f} s]")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--depuis", type=int, default=0)
    p.add_argument("--etape", type=int)
    args = p.parse_args()

    numeros = [args.etape] if args.etape is not None else [
        n for n in sorted(ETAPES) if n >= args.depuis
    ]
    debut = time.perf_counter()
    for n in numeros:
        executer(n)
    print(f"\nChaîne terminée en {(time.perf_counter() - debut) / 60:.1f} minutes.")


if __name__ == "__main__":
    main()

"""
Téléchargement des sources externes du projet.

Toutes les sources passent par le catalogue humanitaire HDX plutôt que par le
portail national datos.gov.co, qui refuse les requêtes automatisées. Les jeux
sont les mêmes ; HDX en republie une copie stable et citable.

Usage :
    python src/telecharger_donnees.py
    python src/telecharger_donnees.py --forcer
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DATA_BRUT  # noqa: E402
from utils import log  # noqa: E402

ENTETES = {"User-Agent": "OTE-analyse-deplacement/1.0 (recherche appliquee)"}
BASE = "https://data.humdata.org/dataset"

SOURCES = [
    {
        "nom": "Registre unique des victimes, faits victimisants par municipalité",
        "fichier": "hechos_victimizantes.csv",
        "url": f"{BASE}/7a82edf4-a7e2-4492-9801-5622767a2949/resource/"
               "1c03eea7-1227-42ae-a1be-e9f08fe1392f/download/hechos_victimizantes_agosto_2023.csv",
        "catalogue": f"{BASE}/colombia-hechos-victimizantes-uariv",
        "licence": "Creative Commons Attribution International",
        "note": "Environ 64 Mo. Extraction arrêtée en août 2023, d'où l'exclusion de 2023.",
    },
    {
        "nom": "Limites administratives, niveaux 0 à 2",
        "fichier": "col_admin_shapefiles.zip",
        "url": f"{BASE}/50ea7fee-f9af-45a7-8a52-abb9c790a0b6/resource/"
               "32fba556-0109-4d1c-84cb-c8abddf7775b/download/col-administrative-divisions-shapefiles.zip",
        "catalogue": f"{BASE}/cod-ab-col",
        "licence": "Creative Commons Attribution International",
        "note": "Environ 117 Mo. Millésime 2020, géométries non simplifiées.",
    },
    {
        "nom": "Population municipale projetée 2024",
        "fichier": "col_admpop_adm2_2024.csv",
        "url": f"{BASE}/8520e386-9263-48c9-b1bf-b2349e019fbb/resource/"
               "76e12f52-af0d-45b2-8024-e6b0e63913c4/download/col_admpop_adm2_2024.csv",
        "catalogue": f"{BASE}/cod-ps-col",
        "licence": "Creative Commons Attribution International",
    },
    {
        "nom": "Cultures de coca par municipalité, 2001 à 2013 (SIDIH)",
        "fichier": "sidih_coca.csv",
        "url": f"{BASE}/a5c4d25f-bfea-4b23-995d-ad90c9931ffc/resource/"
               "449d1d06-3723-4e12-a1ab-2a0b91db29d5/download/sidih_384.csv",
        "catalogue": f"{BASE}/sidih-cultivos-de-coca",
        "licence": "Creative Commons Attribution International",
        "note": "Utilisé en annexe seulement. Les totaux nationaux valent environ "
                "trois fois les chiffres publiés par l'ONUDC : voir data/README_data.md.",
    },
]


def telecharger(source: dict, forcer: bool = False) -> None:
    cible = DATA_BRUT / source["fichier"]
    if cible.exists() and cible.stat().st_size > 0 and not forcer:
        log(f"déjà présent : {source['fichier']} ({cible.stat().st_size / 1e6:.1f} Mo)")
        return

    log(f"téléchargement : {source['nom']}")
    cible.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(source["url"], headers=ENTETES, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(cible, "wb") as f:
            for bloc in r.iter_content(chunk_size=1 << 20):
                f.write(bloc)
    log(f"   écrit : {cible.name} ({cible.stat().st_size / 1e6:.1f} Mo)")


def extraire_limites() -> None:
    archive = DATA_BRUT / "col_admin_shapefiles.zip"
    dossier = DATA_BRUT / "col_admin_shapefiles"
    if dossier.exists() and any(dossier.rglob("*adm2*.shp")):
        log("limites administratives déjà extraites")
        return
    if not archive.exists():
        log("archive des limites absente, extraction impossible")
        return
    with zipfile.ZipFile(archive) as z:
        z.extractall(dossier)
    log(f"   extrait : {dossier.name}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--forcer", action="store_true", help="retélécharge même si présent")
    args = p.parse_args()

    for source in SOURCES:
        telecharger(source, forcer=args.forcer)
    extraire_limites()


if __name__ == "__main__":
    main()

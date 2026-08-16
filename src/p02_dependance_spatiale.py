"""
Étape 2 : matrices de voisinage et dépendance spatiale.

La question posée est simple : le déplacement forcé se concentre-t-il en grappes
qui traversent les frontières municipales, ou chaque municipalité suit-elle sa
propre trajectoire ? C'est la réponse à cette question qui décide si l'unité
d'allocation d'un programme de stabilisation doit rester la municipalité.

Le script produit :
  - deux matrices de voisinage, k plus proches voisins et contiguïté de type reine
  - l'indice de Moran global année par année, avec inférence par permutation
  - les indicateurs locaux d'association spatiale pour les années charnières

Sorties :
  data/processed/voisinages.pkl
  data/processed/lisa.parquet
  outputs/tables/02_*.csv
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    ANNEES_LISA,
    CRS_METRIQUE,
    DATA_TRAITE,
    K_VOISINS,
    PERMUTATIONS,
    SEUIL_SIGNIFICATIVITE,
    TABLEAUX,
)
from utils import etape, exiger, log  # noqa: E402

VARIABLE = "as_deplacement"

# Graine fixée : l'inférence de Moran repose sur des permutations aléatoires, et
# un résultat non reproductible n'est pas un résultat.
GRAINE = 20260814


def construire_voisinages(municipios: gpd.GeoDataFrame) -> dict:
    from libpysal import weights

    projete = municipios.to_crs(CRS_METRIQUE)

    # Les k plus proches voisins sont calculés sur les centroïdes projetés. Un
    # calcul sur des degrés décimaux déformerait le voisinage du nord au sud du
    # pays, la Colombie s'étendant de part et d'autre de l'équateur.
    w_knn = weights.KNN.from_dataframe(projete, k=K_VOISINS, use_index=False)
    w_knn.transform = "r"

    w_reine = weights.Queen.from_dataframe(projete, use_index=False)
    iles = [i for i, n in w_reine.cardinalities.items() if n == 0]
    log(
        f"contiguïté de type reine : {w_reine.mean_neighbors:.1f} voisins en moyenne, "
        f"{len(iles)} entité(s) sans voisin"
    )
    if iles:
        log(
            "  ces entités isolées sont la raison pour laquelle la matrice "
            "principale retenue est celle des k plus proches voisins : "
            "une ligne vide rend la matrice non inversible dans un modèle à "
            "décalage spatial."
        )
    w_reine.transform = "r"

    log(f"k plus proches voisins : k = {K_VOISINS}, {w_knn.n} entités")
    return {"knn": w_knn, "reine": w_reine, "ordre": municipios["divipola"].tolist()}


def moran_par_annee(panel: pd.DataFrame, w, ordre: list[str]) -> pd.DataFrame:
    from esda.moran import Moran

    lignes = []
    for annee, groupe in panel.groupby("annee"):
        serie = groupe.set_index("divipola")[VARIABLE].reindex(ordre)
        exiger(serie.notna().all(), f"valeurs manquantes en {annee}")
        mi = Moran(serie.to_numpy(), w, permutations=PERMUTATIONS)
        lignes.append(
            {
                "annee": int(annee),
                "moran_I": mi.I,
                "esperance": mi.EI,
                "z_simule": mi.z_sim,
                "p_simule": mi.p_sim,
                "significatif": mi.p_sim < SEUIL_SIGNIFICATIVITE,
            }
        )
    return pd.DataFrame(lignes)


def lisa_annee(panel: pd.DataFrame, w, ordre: list[str], annee: int) -> pd.DataFrame:
    from esda.moran import Moran_Local

    groupe = panel[panel["annee"] == annee]
    serie = groupe.set_index("divipola")[VARIABLE].reindex(ordre)
    local = Moran_Local(
        serie.to_numpy(), w, permutations=PERMUTATIONS, seed=GRAINE
    )

    # Les quadrants de esda : 1 haut-haut, 2 bas-haut, 3 bas-bas, 4 haut-bas.
    # Bas-haut et haut-bas sont regroupés sous « atypique » : ce sont des
    # municipalités en rupture avec leur voisinage, et les distinguer imposerait
    # une quatrième couleur qui ne passe pas le contrôle de lisibilité.
    etiquettes = {1: "Haut-Haut", 2: "Atypique", 3: "Bas-Bas", 4: "Atypique"}
    classe = pd.Series(local.q, index=ordre).map(etiquettes)
    classe[local.p_sim >= SEUIL_SIGNIFICATIVITE] = "Non significatif"

    return pd.DataFrame(
        {
            "divipola": ordre,
            "annee": annee,
            "valeur": serie.to_numpy(),
            "moran_local": local.Is,
            "p_simule": local.p_sim,
            "classe": classe.to_numpy(),
        }
    )


def main() -> None:
    np.random.seed(GRAINE)

    with etape("chargement"):
        municipios = gpd.read_file(DATA_TRAITE / "municipios.gpkg", layer="municipios")
        municipios = municipios.sort_values("divipola").reset_index(drop=True)
        panel = pd.read_parquet(DATA_TRAITE / "panel.parquet")
        log(f"{len(municipios)} municipalités, {panel['annee'].nunique()} années")

    with etape("construction des matrices de voisinage"):
        voisinages = construire_voisinages(municipios)
        ordre = voisinages["ordre"]

    with etape("indice de Moran global, année par année"):
        moran = moran_par_annee(panel, voisinages["knn"], ordre)
        moran.to_csv(TABLEAUX / "02_moran_global.csv", index=False)
        log("\n" + moran.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
        log(
            f"\nannées où la dépendance spatiale est significative à "
            f"{SEUIL_SIGNIFICATIVITE:.0%} : {int(moran['significatif'].sum())} sur {len(moran)}"
        )

        # Contrôle de robustesse : le même indice sous contiguïté de type reine.
        moran_reine = moran_par_annee(panel, voisinages["reine"], ordre)
        comparaison = moran[["annee", "moran_I"]].merge(
            moran_reine[["annee", "moran_I"]], on="annee", suffixes=("_knn", "_reine")
        )
        comparaison.to_csv(TABLEAUX / "02_moran_comparaison_matrices.csv", index=False)
        correlation = comparaison["moran_I_knn"].corr(comparaison["moran_I_reine"])
        log(f"corrélation des deux séries de Moran : {correlation:.3f}")

    with etape("indicateurs locaux pour les années charnières"):
        morceaux = [lisa_annee(panel, voisinages["knn"], ordre, a) for a in ANNEES_LISA]
        lisa = pd.concat(morceaux, ignore_index=True)
        lisa.to_parquet(DATA_TRAITE / "lisa.parquet", index=False)

        recap = (
            lisa.groupby(["annee", "classe"], as_index=False)
            .size()
            .pivot(index="annee", columns="classe", values="size")
            .fillna(0)
            .astype(int)
        )
        recap.to_csv(TABLEAUX / "02_lisa_repartition.csv")
        log("\nNombre de municipalités par classe :\n" + recap.to_string())

        # Le même contenu que la carte, sous forme de tableau : c'est la
        # contrepartie exigée par la palette, dont une teinte passe sous le
        # rapport de contraste de 3:1 sur fond clair.
        noms = municipios[["divipola", "municipio", "departamento"]]
        lisa.merge(noms, on="divipola").to_csv(
            TABLEAUX / "02_lisa_detail_par_municipalite.csv", index=False
        )

        grappes = lisa[(lisa["classe"] == "Haut-Haut")]
        persistantes = (
            grappes.groupby("divipola").size().rename("annees_en_grappe").reset_index()
        )
        persistantes = persistantes[persistantes["annees_en_grappe"] == len(ANNEES_LISA)]
        persistantes = persistantes.merge(noms, on="divipola")
        persistantes.to_csv(TABLEAUX / "02_grappes_persistantes.csv", index=False)
        log(
            f"\n{len(persistantes)} municipalités appartiennent à une grappe haute "
            f"sur les {len(ANNEES_LISA)} années examinées :"
        )
        if len(persistantes):
            log("\n" + persistantes.head(25).to_string(index=False))

    with etape("écriture des voisinages"):
        with open(DATA_TRAITE / "voisinages.pkl", "wb") as f:
            pickle.dump(voisinages, f)

    log("étape 2 terminée")


if __name__ == "__main__":
    main()

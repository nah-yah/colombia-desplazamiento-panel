"""
Étape 1 : construction du panel municipalité x année.

Le registre unique des victimes recense des personnes, pas des événements, et il
les rattache à la municipalité où le fait s'est produit. Le panel construit ici
compte donc, pour chaque municipalité et chaque année, le nombre de personnes
reconnues victimes de chaque type de fait.

Trois précautions structurent le script :

1. Le panel est rendu complet. Une municipalité-année absente du registre
   signifie zéro victime enregistrée, pas une donnée manquante ; laisser ces
   cases vides ferait disparaître des observations et biaiserait toute moyenne
   vers le haut. La grille complète est donc reconstruite et comblée par des
   zéros.
2. Les codes DIVIPOLA sont normalisés sur cinq caractères avant tout
   rapprochement. Le fichier source les stocke en numérique, ce qui a fait
   perdre le zéro initial des départements 05 et 08.
3. Le dénominateur de population est celui de 2024, unique pour toute la
   période. Ce n'est pas un oubli : dans un modèle à effets fixes municipaux et
   variable dépendante en logarithme, un dénominateur constant dans le temps est
   entièrement absorbé par l'effet fixe et ne modifie aucun coefficient. Il
   n'affecte que les cartes descriptives, où le choix est signalé.

Sorties :
  data/processed/panel.parquet
  data/processed/municipios.gpkg
  outputs/tables/01_*.csv
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    ANNEE_DEBUT,
    ANNEE_FIN,
    CRS_METRIQUE,
    CRS_SOURCE,
    DATA_BRUT,
    DATA_TRAITE,
    DECALAGE_ANNEES,
    HECHO_DEPLACEMENT,
    HECHOS_COMBAT,
    HECHOS_INTIMIDATION,
    HECHOS_VIOLENCE_LETALE,
    TABLEAUX,
)
from utils import etape, exiger, log, trouver_colonne  # noqa: E402


def normaliser_divipola(serie: pd.Series) -> pd.Series:
    """Ramène un code de municipalité à cinq caractères, zéros initiaux compris."""
    texte = serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return texte.str.zfill(5)


# --------------------------------------------------------------------------
# Registre des victimes
# --------------------------------------------------------------------------

def charger_registre() -> pd.DataFrame:
    chemin = DATA_BRUT / "hechos_victimizantes.csv"
    exiger(chemin.exists(), f"registre absent : {chemin}")

    brut = pd.read_csv(
        chemin, encoding="cp1252",
        dtype={"DANE_OCURRENCIA": str, "Mes": str, "Ano": str},
    )
    log(f"registre brut : {len(brut):,} lignes".replace(",", " "))

    brut["annee"] = pd.to_numeric(brut["Ano"], errors="coerce")
    brut["divipola"] = normaliser_divipola(brut["DANE_OCURRENCIA"])

    # Traçabilité du nettoyage : chaque ligne écartée est comptée et le motif
    # est écrit sur disque, pour qu'un relecteur puisse vérifier qu'aucune purge
    # silencieuse n'a eu lieu.
    motifs = []

    hors_annee = ~brut["annee"].between(ANNEE_DEBUT, ANNEE_FIN)
    motifs.append(("Hors de la fenêtre retenue ou année aberrante", int(hors_annee.sum()),
                   int(brut.loc[hors_annee, "total"].sum())))

    sans_commune = brut["divipola"].isin({"00000", "00000"}) | (
        brut["divipola"].str.fullmatch(r"0+")
    )
    motifs.append(("Municipalité non renseignée", int(sans_commune.sum()),
                   int(brut.loc[sans_commune, "total"].sum())))

    code_invalide = ~brut["divipola"].str.fullmatch(r"\d{5}")
    motifs.append(("Code DIVIPOLA non conforme", int(code_invalide.sum()),
                   int(brut.loc[code_invalide, "total"].sum())))

    journal = pd.DataFrame(motifs, columns=["motif", "lignes_ecartees", "victimes_ecartees"])
    journal.to_csv(TABLEAUX / "01_journal_nettoyage.csv", index=False)
    log("\n" + journal.to_string(index=False))

    propre = brut[~(hors_annee | sans_commune | code_invalide)].copy()
    propre["annee"] = propre["annee"].astype(int)
    log(f"registre retenu : {len(propre):,} lignes".replace(",", " "))
    return propre


def pivoter(registre: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par municipalité-année, une colonne par famille de faits."""
    presents = set(registre["HECHO"].unique())
    attendus = (
        [HECHO_DEPLACEMENT] + HECHOS_VIOLENCE_LETALE
        + HECHOS_INTIMIDATION + HECHOS_COMBAT
    )
    absents = [h for h in attendus if h not in presents]
    exiger(
        not absents,
        "libellés HECHO introuvables dans le registre, la configuration est "
        f"désynchronisée du fichier source : {absents}",
    )

    familles = {
        "deplacement": [HECHO_DEPLACEMENT],
        "violence_letale": HECHOS_VIOLENCE_LETALE,
        "intimidation": HECHOS_INTIMIDATION,
        "combat": HECHOS_COMBAT,
    }

    morceaux = []
    for nom, libelles in familles.items():
        sous = registre[registre["HECHO"].isin(libelles)]
        agrege = sous.groupby(["divipola", "annee"], as_index=False)["total"].sum()
        morceaux.append(agrege.rename(columns={"total": nom}).set_index(["divipola", "annee"]))

    table = pd.concat(morceaux, axis=1).reset_index()

    # Déplacement massif : sous-ensemble du déplacement forcé, conservé à part
    # parce qu'un déplacement massif signale une expulsion collective, alors
    # qu'un déplacement individuel peut résulter d'une menace ciblée.
    massif = registre[
        (registre["HECHO"] == HECHO_DEPLACEMENT)
        & (registre["TIPO_DESPLAZAMIENTO"].str.upper() == "MASIVO")
    ]
    massif = (
        massif.groupby(["divipola", "annee"], as_index=False)["total"]
        .sum()
        .rename(columns={"total": "deplacement_massif"})
    )
    table = table.merge(massif, on=["divipola", "annee"], how="left")
    return table


# --------------------------------------------------------------------------
# Géométries et population
# --------------------------------------------------------------------------

def charger_municipios() -> gpd.GeoDataFrame:
    """Limites municipales COD-AB, avec code DIVIPOLA et population 2024."""
    archive = DATA_BRUT / "col_admin_shapefiles.zip"
    dossier = DATA_BRUT / "col_admin_shapefiles"
    if not dossier.exists():
        exiger(archive.exists(), f"limites administratives absentes : {archive}")
        with zipfile.ZipFile(archive) as z:
            z.extractall(dossier)

    candidats = sorted(dossier.rglob("*adm2*.shp")) or sorted(dossier.rglob("*ADM2*.shp"))
    exiger(bool(candidats), f"aucun shapefile de niveau 2 trouvé dans {dossier}")
    couche = gpd.read_file(candidats[0])
    log(f"limites lues : {candidats[0].name}, {len(couche)} entités")

    col_pcode = trouver_colonne(couche.columns, "ADM2_PCODE")
    col_nom = trouver_colonne(couche.columns, "ADM2_ES", "ADM2_EN", "ADM2_NAME")
    col_dept = trouver_colonne(couche.columns, "ADM1_ES", "ADM1_EN", "ADM1_NAME")

    couche = couche.rename(
        columns={col_pcode: "pcode", col_nom: "municipio", col_dept: "departamento"}
    )[["pcode", "municipio", "departamento", "geometry"]]

    # Le code officiel est un DIVIPOLA à cinq chiffres ; COD-AB le préfixe du
    # code ISO du pays.
    couche["divipola"] = couche["pcode"].astype(str).str.replace("^CO", "", regex=True)
    couche["divipola"] = normaliser_divipola(couche["divipola"])

    if couche.crs is None:
        couche = couche.set_crs(CRS_SOURCE)
    couche = couche.to_crs(CRS_SOURCE)

    # Des municipalités apparaissent parfois en plusieurs morceaux dans les
    # exports COD-AB ; elles sont fusionnées pour garantir une entité par code.
    if not couche["divipola"].is_unique:
        avant = len(couche)
        couche = couche.dissolve(by="divipola", aggfunc="first").reset_index()
        log(f"fusion des géométries multiples : {avant} -> {len(couche)} entités")

    population = pd.read_csv(DATA_BRUT / "col_admpop_adm2_2024.csv", dtype={"ADM2_PCODE": str})
    population["divipola"] = normaliser_divipola(
        population["ADM2_PCODE"].str.replace("^CO", "", regex=True)
    )
    population = population.rename(columns={"T_TL": "population"})[["divipola", "population"]]

    couche = couche.merge(population, on="divipola", how="left")

    # Une population nulle ou absente rend indéfini tout taux pour mille et tout
    # logarithme. Ces unités sont retirées de l'échantillon plutôt que corrigées
    # par une valeur plancher arbitraire, et la liste est journalisée : il s'agit
    # de corregimientos départementaux d'Amazonie que le fichier de population
    # ne couvre pas.
    sans_population = couche["population"].isna() | (couche["population"] <= 0)
    if sans_population.any():
        exclues = couche.loc[sans_population, ["divipola", "municipio", "departamento"]]
        log(f"{len(exclues)} municipalité(s) exclue(s) faute de population :")
        log("\n" + exclues.to_string(index=False))
        exclues.to_csv(TABLEAUX / "01_municipalites_exclues.csv", index=False)
        couche = couche[~sans_population].reset_index(drop=True)

    couche["superficie_km2"] = couche.to_crs(CRS_METRIQUE).area / 1e6
    return couche


# --------------------------------------------------------------------------
# Assemblage
# --------------------------------------------------------------------------

def completer_panel(table: pd.DataFrame, municipios: gpd.GeoDataFrame) -> pd.DataFrame:
    """Reconstruit la grille complète municipalité x année et comble par des zéros."""
    annees = range(ANNEE_DEBUT, ANNEE_FIN + 1)
    grille = pd.MultiIndex.from_product(
        [municipios["divipola"].sort_values(), annees], names=["divipola", "annee"]
    ).to_frame(index=False)

    colonnes_faits = [
        "deplacement", "violence_letale", "intimidation", "combat", "deplacement_massif"
    ]
    panel = grille.merge(table, on=["divipola", "annee"], how="left")
    panel[colonnes_faits] = panel[colonnes_faits].fillna(0.0)

    # Les codes présents dans le registre mais absents des limites sont signalés,
    # jamais absorbés en silence : ils correspondent surtout à des municipalités
    # créées ou supprimées après le millésime cartographique.
    inconnus = set(table["divipola"]) - set(municipios["divipola"])
    if inconnus:
        perdus = table[table["divipola"].isin(inconnus)]["deplacement"].sum()
        log(
            f"{len(inconnus)} codes du registre sans géométrie correspondante, "
            f"soit {perdus:,.0f} victimes de déplacement écartées "
            f"({perdus / table['deplacement'].sum():.2%} du total)".replace(",", " ")
        )
        pd.Series(sorted(inconnus), name="divipola").to_csv(
            TABLEAUX / "01_codes_sans_geometrie.csv", index=False
        )

    contexte = municipios[["divipola", "municipio", "departamento", "population", "superficie_km2"]]
    panel = panel.merge(contexte, on="divipola", how="left")
    return panel


def ajouter_variables(panel: pd.DataFrame) -> pd.DataFrame:
    """Taux pour mille, transformations et décalages temporels."""
    pop = panel["population"].replace(0, np.nan)
    for col in ["deplacement", "violence_letale", "intimidation", "combat", "deplacement_massif"]:
        panel[f"taux_{col}"] = panel[col] / pop * 1000

    # Le sinus hyperbolique inverse est retenu plutôt que log(1 + x) : il se
    # comporte comme un logarithme aux valeurs élevées, reste défini en zéro, et
    # ne dépend pas de l'unité choisie pour x autant que log(1 + x).
    for col in ["deplacement", "violence_letale", "intimidation", "combat"]:
        panel[f"as_{col}"] = np.arcsinh(panel[f"taux_{col}"])

    panel = panel.sort_values(["divipola", "annee"]).reset_index(drop=True)
    for col in ["as_violence_letale", "as_intimidation", "as_combat", "as_deplacement"]:
        panel[f"{col}_ret{DECALAGE_ANNEES}"] = panel.groupby("divipola")[col].shift(
            DECALAGE_ANNEES
        )

    panel["log_population"] = np.log(panel["population"])
    return panel


def main() -> None:
    with etape("lecture du registre des victimes"):
        registre = charger_registre()

    with etape("agrégation par municipalité et année"):
        table = pivoter(registre)
        log(f"{len(table):,} couples municipalité-année observés".replace(",", " "))

    with etape("lecture des limites municipales"):
        municipios = charger_municipios()

    with etape("complétion du panel"):
        panel = completer_panel(table, municipios)
        panel = ajouter_variables(panel)
        n_mun = panel["divipola"].nunique()
        n_an = panel["annee"].nunique()
        exiger(
            len(panel) == n_mun * n_an,
            f"panel non équilibré : {len(panel)} lignes pour {n_mun} x {n_an}",
        )
        log(f"panel équilibré : {n_mun} municipalités x {n_an} années = {len(panel):,} lignes"
            .replace(",", " "))

    with etape("contrôles et écriture"):
        national = (
            panel.groupby("annee", as_index=False)
            .agg(
                deplacement=("deplacement", "sum"),
                massif=("deplacement_massif", "sum"),
                violence_letale=("violence_letale", "sum"),
                municipalites_touchees=("deplacement", lambda s: int((s > 0).sum())),
            )
        )
        national["part_massif"] = national["massif"] / national["deplacement"]
        national.to_csv(TABLEAUX / "01_serie_nationale.csv", index=False)
        affichage = national.copy()
        affichage["part_massif"] = (affichage["part_massif"] * 100).round(1)
        affichage = affichage.rename(columns={"part_massif": "part_massif_pct"})
        log("\n" + affichage.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

        zeros = (panel["deplacement"] == 0).mean()
        log(f"part de municipalité-années sans aucun déplacement enregistré : {zeros:.1%}")

        panel.to_parquet(DATA_TRAITE / "panel.parquet", index=False)
        municipios.to_file(DATA_TRAITE / "municipios.gpkg", layer="municipios", driver="GPKG")

    log("étape 1 terminée")


if __name__ == "__main__":
    main()

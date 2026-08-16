"""
Étape 4 : cartes et graphiques.

Six sorties dans outputs/figures. Les géométries municipales sont simplifiées à
500 mètres avant tracé : à l'échelle d'une carte nationale, cette tolérance est
inférieure à l'épaisseur du trait, et elle divise par plus de dix le temps de
rendu d'une couche de 92 Mo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import style  # noqa: E402
from config import (  # noqa: E402
    ANNEE_DEBUT,
    ANNEE_FIN,
    ANNEES_LISA,
    CRS_METRIQUE,
    DATA_TRAITE,
    DPI_FIGURES,
    FIGURES,
    K_VOISINS,
    TABLEAUX,
)
from utils import etape, log  # noqa: E402

SOURCE = (
    "Sources : Unité pour les victimes (registre unique, extraction août 2023), "
    "OCHA COD-AB et COD-PS. Analyse : Observatoire territorial pour la stabilisation (cas d'école)."
)


def charger():
    municipios = gpd.read_file(DATA_TRAITE / "municipios.gpkg", layer="municipios")
    municipios = municipios.sort_values("divipola").reset_index(drop=True)
    municipios = municipios.to_crs(CRS_METRIQUE)
    municipios["geometry"] = municipios.geometry.simplify(500)
    panel = pd.read_parquet(DATA_TRAITE / "panel.parquet")
    lisa = pd.read_parquet(DATA_TRAITE / "lisa.parquet")
    return municipios, panel, lisa


def enregistrer(fig, nom: str) -> None:
    chemin = FIGURES / nom
    fig.savefig(chemin, dpi=DPI_FIGURES, bbox_inches="tight", facecolor=style.SURFACE)
    plt.close(fig)
    log(f"figure écrite : {chemin.name}")


# --------------------------------------------------------------------------

def fig_serie_nationale() -> None:
    national = pd.read_csv(TABLEAUX / "01_serie_nationale.csv")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.grid(axis="y", zorder=0)

    ax.plot(national["annee"], national["deplacement"] / 1000,
            color=style.SERIE_1, lw=2, zorder=3)
    ax.fill_between(national["annee"], national["deplacement"] / 1000,
                    color=style.SERIE_1, alpha=0.10, zorder=2)

    pic = national.loc[national["deplacement"].idxmax()]
    ax.annotate(
        f"{pic['deplacement'] / 1000:.0f} milliers\nen {int(pic['annee'])}",
        (pic["annee"], pic["deplacement"] / 1000),
        textcoords="offset points", xytext=(10, -6), fontsize=9,
        color=style.ENCRE_PRINCIPALE, weight="semibold",
    )
    fin = national.iloc[-1]
    ax.annotate(
        f"{fin['deplacement'] / 1000:.0f} en {int(fin['annee'])}",
        (fin["annee"], fin["deplacement"] / 1000),
        textcoords="offset points", xytext=(-8, 12), ha="right", fontsize=9,
        color=style.ENCRE_SECONDAIRE,
    )

    ax.set_ylabel("Victimes de déplacement forcé (milliers)")
    ax.set_xlabel("Année du fait")
    style.titrer(
        ax,
        "Le déplacement forcé recule, sans disparaître",
        f"Personnes reconnues victimes, par année de survenue du fait, {ANNEE_DEBUT} à {ANNEE_FIN}. "
        "La remontée de 2021 et 2022 suit la recomposition des groupes armés dans les zones "
        "laissées par les FARC.",
    )
    enregistrer(fig, "fig01_serie_nationale.png")


def fig_moran() -> None:
    moran = pd.read_csv(TABLEAUX / "02_moran_global.csv")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.grid(axis="y", zorder=0)

    ax.axhline(0, color=style.LIGNE_BASE, lw=1, zorder=1)
    ax.plot(moran["annee"], moran["moran_I"], color=style.SERIE_1, lw=2, zorder=3)

    significatif = moran[moran["significatif"]]
    ax.scatter(significatif["annee"], significatif["moran_I"], s=34,
               color=style.SERIE_1, zorder=4, edgecolor=style.SURFACE, linewidths=1.8,
               label=f"Significatif à 5 % ({len(significatif)} années sur {len(moran)})")
    non = moran[~moran["significatif"]]
    if len(non):
        ax.scatter(non["annee"], non["moran_I"], s=34, facecolor=style.SURFACE,
                   edgecolor=style.ENCRE_ATTENUEE, linewidths=1.2, zorder=4,
                   label="Non significatif")

    for i in (0, len(moran) - 1):
        ax.annotate(
            f"{moran['moran_I'].iloc[i]:.2f}",
            (moran["annee"].iloc[i], moran["moran_I"].iloc[i]),
            textcoords="offset points", xytext=(0, 12), ha="center",
            fontsize=9, color=style.ENCRE_PRINCIPALE, weight="semibold",
        )

    ax.set_ylabel("Indice de Moran de la variable dépendante")
    ax.set_xlabel("Année")
    ax.legend(labelcolor=style.ENCRE_SECONDAIRE, loc="lower left")
    style.titrer(
        ax,
        "Le déplacement est resté un phénomène de grappes, toute la période",
        f"Voisinage des {K_VOISINS} plus proches voisins, inférence par permutation. "
        "L'indice ne faiblit pas après l'accord de paix de 2016 : le volume baisse, "
        "la structure spatiale tient.",
    )
    enregistrer(fig, "fig02_moran_global.png")


def fig_taux_moyen(municipios, panel) -> None:
    moyenne = (
        panel.groupby("divipola", as_index=False)["taux_deplacement"].mean()
        .rename(columns={"taux_deplacement": "taux_moyen"})
    )
    carte = municipios.merge(moyenne, on="divipola", how="left")

    fig, ax = plt.subplots(figsize=(7.5, 9))
    carte.plot(
        column="taux_moyen", ax=ax, cmap=style.CMAP_TEMPS, scheme="quantiles", k=6,
        edgecolor=style.LIGNE_BASE, linewidth=0.15, legend=True,
        legend_kwds={"title": "Victimes pour 1 000 habitants,\nmoyenne annuelle",
                     "loc": "lower left", "fontsize": 8.5, "title_fontsize": 9},
        missing_kwds={"color": style.FOND_TERRE},
    )
    style.habiller_carte(
        ax,
        "Intensité moyenne du déplacement forcé, 2000-2022",
        "Dénominateur de population 2024, constant sur la période. Classes en sextiles.",
        SOURCE,
    )
    enregistrer(fig, "fig03_taux_moyen.png")


def fig_lisa(municipios, lisa) -> None:
    fig, axes = plt.subplots(1, len(ANNEES_LISA), figsize=(3.5 * len(ANNEES_LISA), 8.2))
    for ax, annee in zip(np.atleast_1d(axes), ANNEES_LISA):
        sous = lisa[lisa["annee"] == annee][["divipola", "classe"]]
        carte = municipios.merge(sous, on="divipola", how="left")
        carte["couleur"] = carte["classe"].map(style.COULEURS_LISA).fillna(style.FOND_TERRE)
        carte.plot(ax=ax, color=carte["couleur"], edgecolor=style.LIGNE_BASE, linewidth=0.1)
        ax.set_axis_off()
        n_hh = int((carte["classe"] == "Haut-Haut").sum())
        ax.set_title(f"{annee}\n{n_hh} municipalités en grappe haute",
                     fontsize=10.5, color=style.ENCRE_PRINCIPALE)

    fig.subplots_adjust(top=0.86, bottom=0.10, left=0.02, right=0.98, wspace=0.02)
    fig.legend(
        handles=[Patch(facecolor=c, edgecolor=style.LIGNE_BASE, label=n)
                 for n, c in style.COULEURS_LISA.items()],
        loc="lower center", ncol=4, frameon=False, labelcolor=style.ENCRE_SECONDAIRE,
        bbox_to_anchor=(0.5, 0.045),
    )
    fig.text(
        0.03, 0.955, "Les grappes de déplacement forcé ne se déplacent pas",
        ha="left", fontsize=14, weight="semibold", color=style.ENCRE_PRINCIPALE,
    )
    fig.text(
        0.03, 0.915,
        "Indicateurs locaux d'association spatiale, seuil de 5 %. Vingt ans séparent la première "
        "carte de la dernière, et le nombre de municipalités en grappe haute varie à peine.\n"
        "Le détail par municipalité est exporté en tableau dans outputs/tables.",
        fontsize=9.5, color=style.ENCRE_SECONDAIRE, va="top",
    )
    fig.text(0.03, 0.015, SOURCE, fontsize=8, color=style.ENCRE_ATTENUEE)
    enregistrer(fig, "fig04_lisa_annees_charnieres.png")


def fig_grappes_persistantes(municipios, lisa) -> None:
    compte = (
        lisa[lisa["classe"] == "Haut-Haut"].groupby("divipola").size()
        .rename("annees").reset_index()
    )
    carte = municipios.merge(compte, on="divipola", how="left")
    carte["annees"] = carte["annees"].fillna(0).astype(int)

    fig, ax = plt.subplots(figsize=(7.5, 9))
    carte.plot(ax=ax, color=style.FOND_TERRE, edgecolor=style.LIGNE_BASE, linewidth=0.15)
    rampe = [style.RAMPE_BLEUE[3], style.RAMPE_BLEUE[6], style.RAMPE_BLEUE[9], style.RAMPE_BLEUE[12]]
    for n in range(1, len(ANNEES_LISA) + 1):
        sous = carte[carte["annees"] == n]
        if len(sous):
            sous.plot(ax=ax, color=rampe[n - 1], edgecolor=style.LIGNE_BASE, linewidth=0.15)

    ax.legend(
        handles=[Patch(facecolor=rampe[n - 1], label=f"{n} année sur {len(ANNEES_LISA)}"
                       if n == 1 else f"{n} années sur {len(ANNEES_LISA)}")
                 for n in range(1, len(ANNEES_LISA) + 1)],
        loc="lower left", labelcolor=style.ENCRE_SECONDAIRE, title="Appartenance à une grappe haute",
        title_fontsize=9, fontsize=8.5,
    )
    persistantes = int((carte["annees"] == len(ANNEES_LISA)).sum())
    style.habiller_carte(
        ax,
        "Les grappes ne se déplacent pas beaucoup",
        f"{persistantes} municipalités appartiennent à une grappe haute sur les quatre années "
        "examinées. Ce sont elles qui décrivent une géographie structurelle, non conjoncturelle.",
        SOURCE,
    )
    enregistrer(fig, "fig05_grappes_persistantes.png")


def fig_effets() -> None:
    effets = pd.read_csv(TABLEAUX / "03_effets_directs_indirects.csv")
    effets = effets.sort_values("effet_total")

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.grid(axis="x", zorder=0)
    y = np.arange(len(effets))
    hauteur = 0.34

    ax.barh(y + hauteur / 2, effets["effet_direct"], hauteur * 0.92,
            color=style.RAMPE_SEUILS[2], label="Effet direct, dans la municipalité", zorder=3)
    ax.barh(y - hauteur / 2, effets["effet_indirect"], hauteur * 0.92,
            color=style.RAMPE_SEUILS[0], label="Effet indirect, déversé sur les voisines", zorder=3)

    # La part déversée est la même pour les trois variables, puisqu'elle ne
    # dépend que de rho et du voisinage. L'écrire une fois dans le sous-titre
    # suffit ; la répéter sur chaque barre n'ajouterait que de l'encre.
    part = effets["part_deversee"].iloc[0]

    ax.set_yticks(y)
    ax.set_yticklabels([v.replace(", décalée", ",\ndécalée").replace(", décalés", ",\ndécalés")
                        for v in effets["variable"]], fontsize=9)
    ax.set_xlabel("Effet marginal sur le déplacement forcé (échelle asinh)")
    ax.legend(labelcolor=style.ENCRE_SECONDAIRE, loc="lower right")
    style.titrer(
        ax,
        f"{part:.0%} de l'effet se produit hors de la municipalité touchée",
        "Décomposition des coefficients du modèle à décalage spatial. La part déversée ne dépend "
        "que du paramètre spatial et du voisinage : elle est donc identique\npour les trois "
        "variables, seule leur intensité diffère.",
    )
    ax.margins(x=0.12)
    enregistrer(fig, "fig06_effets_directs_indirects.png")


def main() -> None:
    style.appliquer()
    with etape("chargement"):
        municipios, panel, lisa = charger()

    with etape("graphiques de série"):
        fig_serie_nationale()
        fig_moran()

    with etape("cartes"):
        fig_taux_moyen(municipios, panel)
        fig_lisa(municipios, lisa)
        fig_grappes_persistantes(municipios, lisa)

    with etape("effets du modèle"):
        fig_effets()

    log("étape 4 terminée")


if __name__ == "__main__":
    main()

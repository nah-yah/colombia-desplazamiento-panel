"""
Jetons graphiques et réglages matplotlib communs à toutes les sorties.

Deux familles de couleurs sont définies : une rampe séquentielle bleue, monotone
en clarté, pour les quantités, et un triplet catégoriel bleu / rouge / jaune pour
les classes LISA. Le triplet passe le contrôle de séparation en vision déficiente
sur toutes les paires (ΔE 15,3 en deutéranopie, plancher exigé 8).

Le jaune tombe sous le rapport de contraste 3:1 sur fond clair. Là où il sert, la
légende est explicitement libellée et le même contenu exporté en tableau CSV, de
sorte que l'information ne repose pas sur la seule couleur.
"""

from __future__ import annotations

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

# --------------------------------------------------------------------------
# Surfaces et encres
# --------------------------------------------------------------------------

SURFACE = "#fcfcfb"
ENCRE_PRINCIPALE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"
ENCRE_ATTENUEE = "#898781"
GRILLE = "#e1e0d9"
LIGNE_BASE = "#c3c2b7"

# Fond des municipalités sans donnée ou hors classe significative.
FOND_TERRE = "#f0efec"

# --------------------------------------------------------------------------
# Rampe séquentielle : une seule teinte, du clair au foncé
# --------------------------------------------------------------------------

# Le taux de déplacement est une grandeur continue : rampe à teinte unique. Un
# dégradé arc-en-ciel donnerait l'illusion de seuils là où la variation est
# continue.
RAMPE_BLEUE = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
    "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]
CMAP_SEQUENTIELLE = LinearSegmentedColormap.from_list("taux_deplacement", RAMPE_BLEUE)

# Rampe ordinale à trois crans, utilisée pour les barres d'effets directs et
# indirects. Le cran le plus clair reste au-dessus de 2:1 sur la surface, pour
# qu'une barre claire ne se confonde pas avec le fond.
RAMPE_SEUILS = ["#86b6ef", "#2a78d6", "#104281"]

# --------------------------------------------------------------------------
# Séries de courbes
# --------------------------------------------------------------------------

SERIE_1 = "#2a78d6"
SERIE_2 = "#eb6834"

# --------------------------------------------------------------------------
# Classes LISA
# --------------------------------------------------------------------------

# Quatre modalités sont ramenées à trois classes colorées plus une neutre. Sur
# une carte choroplèthe, n'importe quelles deux couleurs peuvent se retrouver
# côte à côte : le triplet est donc validé sur toutes les paires, pas seulement
# sur les paires attendues.
#
# Les valeurs atypiques haut-bas et bas-haut sont fusionnées en une seule
# classe. Les séparer imposerait une quatrième couleur, et aucun quatuor de la
# palette ne passe le contrôle toutes paires. Elles sont peu nombreuses et
# portent le même message, celui d'une municipalité en rupture avec son
# voisinage.
COULEURS_LISA = {
    "Haut-Haut": "#e34948",
    "Bas-Bas": "#2a78d6",
    "Atypique": "#eda100",
    "Non significatif": "#f0efec",
}

# --------------------------------------------------------------------------
# Réglages matplotlib
# --------------------------------------------------------------------------

def appliquer() -> None:
    """Applique les réglages de rendu à l'ensemble du processus."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "semibold",
        "axes.titlecolor": ENCRE_PRINCIPALE,
        "axes.labelcolor": ENCRE_SECONDAIRE,
        "axes.labelsize": 10,
        "axes.edgecolor": LIGNE_BASE,
        "axes.linewidth": 0.8,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": GRILLE,
        "grid.linewidth": 0.8,
        "xtick.color": ENCRE_ATTENUEE,
        "ytick.color": ENCRE_ATTENUEE,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "figure.dpi": 110,
    })


def titrer(ax, titre: str, sous_titre: str = "", source: str = "") -> None:
    """
    Pose titre, sous-titre et source au-dessus d'un graphique.

    Le placement se fait en coordonnées d'axes, et non par `set_title` et
    `figure.text` : mélanger les deux systèmes fait se chevaucher les deux
    textes dès que la figure change de taille.
    """
    ax.set_title("")
    haut = 1.17 if sous_titre else 1.04
    ax.text(
        0.0, haut, titre, transform=ax.transAxes, fontsize=13, weight="semibold",
        color=ENCRE_PRINCIPALE, va="bottom",
    )
    if sous_titre:
        ax.text(
            0.0, 1.035, sous_titre, transform=ax.transAxes, fontsize=9.5,
            color=ENCRE_SECONDAIRE, va="bottom",
        )
    if source:
        ax.text(
            0.0, -0.16, source, transform=ax.transAxes, fontsize=8,
            color=ENCRE_ATTENUEE, va="top",
        )


def habiller_carte(ax, titre: str, sous_titre: str = "", source: str = "") -> None:
    """Retire les axes d'une carte et pose titre, sous-titre et mention de source."""
    ax.set_axis_off()
    ax.set_title("")
    ax.text(
        0.0, 1.06, titre, transform=ax.transAxes, fontsize=13, weight="semibold",
        color=ENCRE_PRINCIPALE, va="bottom",
    )
    if sous_titre:
        ax.text(
            0.0, 1.015, sous_titre, transform=ax.transAxes, fontsize=9.5,
            color=ENCRE_SECONDAIRE, va="bottom",
        )
    if source:
        ax.text(
            0.0, -0.03, source, transform=ax.transAxes, fontsize=8,
            color=ENCRE_ATTENUEE, va="top",
        )

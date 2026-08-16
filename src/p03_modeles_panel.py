"""
Étape 3 : modèles de panel spatiaux.

Trois spécifications sont estimées sur le même échantillon :

  M1  effets fixes à deux voies, sans terme spatial
  M2  modèle à décalage spatial de la variable dépendante (SAR), effets fixes
  M3  modèle à erreur spatialement autocorrélée (SEM), effets fixes

M1 sert de référence et ses résidus de diagnostic. Si le déplacement forcé
n'était structuré spatialement que par les variables explicatives, les résidus
de M1 seraient dispersés au hasard sur le territoire ; s'ils restent groupés, le
modèle non spatial est mal spécifié et appelle un terme spatial.

Le diagnostic est l'indice de Moran calculé sur les résidus de M1, année par
année, et non les tests du multiplicateur de Lagrange pour données de panel :
leur implémentation dans spreg construit une matrice pleine de dimension
(n x t) au carré, soit 4,5 Go pour ce panel de 24 662 observations. Le Moran des
résidus répond à la même question en quelques secondes de calcul.

Les effets fixes municipaux absorbent ce qui, dans une municipalité, ne bouge
pas sur la période : relief, distance aux marchés, présence historique d'un
groupe armé, qualité de l'enregistrement administratif local. Les effets d'année
absorbent les chocs nationaux, dont l'accord de paix de 2016 et les changements
de doctrine d'enregistrement du registre.

Ces modèles ne mesurent pas d'effet causal ; ils estiment une structure de
dépendance, c'est-à-dire dans quelle mesure le déplacement d'une municipalité
s'explique par ce qui se passe chez ses voisines, une fois retirés ce qui lui
est propre et ce qui est commun à toutes. Les limites de l'exercice sont
détaillées dans le README.

Sorties : outputs/tables/03_*.csv
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    ANNEE_DEBUT,
    ANNEE_FIN,
    DATA_TRAITE,
    DECALAGE_ANNEES,
    PERMUTATIONS,
    TABLEAUX,
)
from utils import etape, exiger, log  # noqa: E402

DEPENDANTE = "as_deplacement"
EXPLICATIVES = [
    f"as_violence_letale_ret{DECALAGE_ANNEES}",
    f"as_intimidation_ret{DECALAGE_ANNEES}",
    f"as_combat_ret{DECALAGE_ANNEES}",
]
LIBELLES = {
    f"as_violence_letale_ret{DECALAGE_ANNEES}": "Violence létale, décalée d'un an",
    f"as_intimidation_ret{DECALAGE_ANNEES}": "Menaces, décalées d'un an",
    f"as_combat_ret{DECALAGE_ANNEES}": "Combats et engins explosifs, décalés d'un an",
}


# --------------------------------------------------------------------------
# Préparation de la matrice du panel
# --------------------------------------------------------------------------

def preparer(panel: pd.DataFrame, ordre: list[str]):
    """
    Met le panel en forme empilée, dans l'ordre attendu par spreg.

    spreg attend un empilement par période : les n municipalités de la première
    année, puis les n de la deuxième, et ainsi de suite. L'ordre des unités doit
    être exactement celui de la matrice de voisinage, sans quoi les poids
    portent sur les mauvais voisins et l'estimation aboutit sans lever d'erreur.
    """
    # Le décalage d'un an consomme la première année de la fenêtre.
    annees = sorted(a for a in panel["annee"].unique() if a > ANNEE_DEBUT)
    sous = panel[panel["annee"].isin(annees)].copy()

    colonnes = [DEPENDANTE] + EXPLICATIVES
    sous = sous.dropna(subset=colonnes)
    exiger(
        len(sous) == len(ordre) * len(annees),
        f"panel déséquilibré après décalage : {len(sous)} lignes "
        f"pour {len(ordre)} x {len(annees)}",
    )

    cube = {}
    for col in colonnes:
        pivot = sous.pivot(index="divipola", columns="annee", values=col).reindex(ordre)
        exiger(pivot.notna().all().all(), f"valeurs manquantes dans {col}")
        cube[col] = pivot[annees].to_numpy()

    return cube, annees, sous


def deux_voies(matrice: np.ndarray) -> np.ndarray:
    """
    Retire la moyenne annuelle de chaque colonne.

    Les modèles de panel de spreg absorbent les effets fixes individuels. Les
    effets d'année sont retirés en amont, ici, ce qui revient à estimer un
    modèle à deux voies. Sans cette étape, une tendance nationale commune, par
    exemple la chute générale du déplacement après 2016, serait attribuée à la
    dépendance spatiale : toutes les municipalités baissent en même temps, donc
    chacune ressemble à ses voisines.
    """
    return matrice - matrice.mean(axis=0, keepdims=True)


def empiler(matrice: np.ndarray) -> np.ndarray:
    """(n, t) -> (n*t, 1), empilé par période."""
    return matrice.reshape((-1, 1), order="F")


# --------------------------------------------------------------------------
# Modèle de référence, sans terme spatial
# --------------------------------------------------------------------------

def effets_fixes_ols(cube, annees, ordre):
    """Effets fixes à deux voies estimés par transformation intra-individuelle."""
    import statsmodels.api as sm

    y = deux_voies(cube[DEPENDANTE])
    X = np.column_stack([deux_voies(cube[c]).reshape(-1, order="F") for c in EXPLICATIVES])
    y_plat = y.reshape(-1, order="F")

    # Transformation intra : on retire ensuite la moyenne de chaque municipalité.
    n, t = cube[DEPENDANTE].shape
    y_mat = y_plat.reshape((n, t), order="F")
    y_intra = (y_mat - y_mat.mean(axis=1, keepdims=True)).reshape(-1, order="F")
    X_intra = np.column_stack([
        (col.reshape((n, t), order="F") - col.reshape((n, t), order="F").mean(axis=1, keepdims=True)
         ).reshape(-1, order="F")
        for col in X.T
    ])

    modele = sm.OLS(y_intra, X_intra)
    # Écarts types groupés par municipalité : les observations d'une même
    # municipalité sur vingt ans ne sont pas indépendantes.
    grappes = np.tile(np.arange(n), t)
    resultat = modele.fit(cov_type="cluster", cov_kwds={"groups": grappes})

    table = pd.DataFrame({
        "variable": [LIBELLES[c] for c in EXPLICATIVES],
        "coefficient": resultat.params,
        "ecart_type": resultat.bse,
        "z": resultat.tvalues,
        "p": resultat.pvalues,
    })
    return resultat, table, y_intra, X_intra, grappes


# --------------------------------------------------------------------------
# Effets directs, indirects, totaux
# --------------------------------------------------------------------------

def decomposer_effets(rho: float, betas: np.ndarray, w) -> pd.DataFrame:
    """
    Décompose l'effet d'une variable en part locale et part déversée.

    Dans un modèle à décalage spatial, un coefficient ne se lit pas comme un
    effet marginal. Une hausse dans une municipalité modifie sa propre valeur,
    ce qui modifie celle de ses voisines, ce qui rétroagit sur elle. L'effet
    total vaut beta / (1 - rho) ; l'effet direct inclut la boucle de rétroaction
    et se lit sur la diagonale de l'inverse de (I - rho W) ; la différence est ce
    qui se déverse sur les voisines.

    La part déversée ressort identique pour toutes les variables, par
    construction : le rapport de l'effet indirect à l'effet total ne dépend que
    de rho et de la matrice de voisinage, jamais du coefficient de la variable.
    Un modèle de Durbin spatial, qui ajoute les variables explicatives décalées,
    permettrait des parts distinctes par variable ; il n'est pas estimé ici.
    """
    n = w.n
    W = w.full()[0]
    inverse = np.linalg.inv(np.eye(n) - rho * W)
    trace_moyenne = np.trace(inverse) / n
    somme_moyenne = inverse.sum() / n

    lignes = []
    for nom, beta in zip([LIBELLES[c] for c in EXPLICATIVES], betas):
        direct = trace_moyenne * beta
        total = somme_moyenne * beta
        lignes.append({
            "variable": nom,
            "effet_direct": direct,
            "effet_indirect": total - direct,
            "effet_total": total,
            "part_deversee": (total - direct) / total if total else np.nan,
        })
    return pd.DataFrame(lignes)


# --------------------------------------------------------------------------

def main() -> None:
    with etape("chargement"):
        panel = pd.read_parquet(DATA_TRAITE / "panel.parquet")
        with open(DATA_TRAITE / "voisinages.pkl", "rb") as f:
            voisinages = pickle.load(f)
        w = voisinages["knn"]
        ordre = voisinages["ordre"]
        cube, annees, sous = preparer(panel, ordre)
        log(
            f"échantillon d'estimation : {len(ordre)} municipalités x {len(annees)} années "
            f"({annees[0]} à {annees[-1]}) = {len(ordre) * len(annees):,} observations"
            .replace(",", " ")
        )

    with etape("M1, effets fixes à deux voies sans terme spatial"):
        resultat_ols, table_ols, y_intra, X_intra, grappes = effets_fixes_ols(cube, annees, ordre)
        table_ols["modele"] = "M1 effets fixes"
        log("\n" + table_ols.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
        log(f"R2 intra : {resultat_ols.rsquared:.4f}")

    with etape("dépendance spatiale résiduelle de M1"):
        import spreg
        from esda.moran import Moran

        y_emp = empiler(deux_voies(cube[DEPENDANTE]))
        X_emp = np.column_stack([empiler(deux_voies(cube[c])).ravel() for c in EXPLICATIVES])

        n, t = cube[DEPENDANTE].shape
        residus = np.asarray(resultat_ols.resid).reshape((n, t), order="F")

        lignes = []
        for j, annee in enumerate(annees):
            mi = Moran(residus[:, j], w, permutations=PERMUTATIONS)
            lignes.append({
                "annee": int(annee), "moran_residus": mi.I, "p_simule": mi.p_sim,
                "significatif": mi.p_sim < 0.05,
            })
        diagnostic = pd.DataFrame(lignes)
        diagnostic.to_csv(TABLEAUX / "03_moran_residus.csv", index=False)
        log(
            f"  Moran des résidus : médiane {diagnostic['moran_residus'].median():.3f}, "
            f"significatif dans {int(diagnostic['significatif'].sum())} années sur {len(diagnostic)}"
        )
        log(
            "  Une dépendance résiduelle significative indique que les violences "
            "locales n'épuisent pas la structure spatiale du déplacement."
        )

    with etape("M2, décalage spatial avec effets fixes"):
        m2 = spreg.Panel_FE_Lag(
            y_emp, X_emp, w,
            name_y="Déplacement forcé (asinh du taux)",
            name_x=[LIBELLES[c] for c in EXPLICATIVES],
            name_ds="Registre unique des victimes, UARIV",
        )
        rho = float(np.asarray(m2.betas).ravel()[-1])
        betas_m2 = np.asarray(m2.betas).ravel()[: len(EXPLICATIVES)]
        erreurs_m2 = np.asarray(m2.std_err).ravel()[: len(EXPLICATIVES)]
        log(f"  rho estimé : {rho:.4f}")
        log(
            "  Un rho positif : le déplacement d'une municipalité est d'autant "
            "plus élevé que celui de ses voisines l'est."
        )

        table_m2 = pd.DataFrame({
            "variable": [LIBELLES[c] for c in EXPLICATIVES],
            "coefficient": betas_m2,
            "ecart_type": erreurs_m2,
            "modele": "M2 décalage spatial",
        })
        table_m2["z"] = table_m2["coefficient"] / table_m2["ecart_type"]

    with etape("M3, erreur spatialement autocorrélée avec effets fixes"):
        m3 = spreg.Panel_FE_Error(
            y_emp, X_emp, w,
            name_y="Déplacement forcé (asinh du taux)",
            name_x=[LIBELLES[c] for c in EXPLICATIVES],
            name_ds="Registre unique des victimes, UARIV",
        )
        lambda_ = float(np.asarray(m3.betas).ravel()[-1])
        betas_m3 = np.asarray(m3.betas).ravel()[: len(EXPLICATIVES)]
        erreurs_m3 = np.asarray(m3.std_err).ravel()[: len(EXPLICATIVES)]
        log(f"  lambda estimé : {lambda_:.4f}")

        table_m3 = pd.DataFrame({
            "variable": [LIBELLES[c] for c in EXPLICATIVES],
            "coefficient": betas_m3,
            "ecart_type": erreurs_m3,
            "modele": "M3 erreur spatiale",
        })
        table_m3["z"] = table_m3["coefficient"] / table_m3["ecart_type"]

    with etape("choix entre les deux formes spatiales"):
        # À nombre de paramètres égal, la vraisemblance départage directement.
        ajustement = pd.DataFrame([
            {"modele": "M2 décalage spatial", "log_vraisemblance": float(m2.logll),
             "AIC": float(m2.aic), "parametre_spatial": rho},
            {"modele": "M3 erreur spatiale", "log_vraisemblance": float(m3.logll),
             "AIC": float(m3.aic), "parametre_spatial": lambda_},
        ])
        ajustement.to_csv(TABLEAUX / "03_ajustement_modeles.csv", index=False)
        log("\n" + ajustement.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
        retenu = ajustement.loc[ajustement["AIC"].idxmin(), "modele"]
        log(f"  Modèle retenu sur le critère d'information : {retenu}")

    with etape("décomposition des effets"):
        effets = decomposer_effets(rho, betas_m2, w)
        effets.to_csv(TABLEAUX / "03_effets_directs_indirects.csv", index=False)
        log("\n" + effets.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
        part_moyenne = effets["part_deversee"].mean()
        log(
            f"\nEn moyenne sur les trois variables, {part_moyenne:.0%} de l'effet total "
            f"se produit hors de la municipalité où le choc a lieu."
        )

    with etape("écriture des résultats"):
        from scipy.stats import norm

        colonnes = ["modele", "variable", "coefficient", "ecart_type", "z", "p"]
        comparaison = pd.concat(
            [table_ols, table_m2, table_m3], ignore_index=True
        ).reindex(columns=colonnes)
        # spreg n'expose pas de p-valeur pour les modèles de panel : elle est
        # reconstituée à partir de la statistique z, sous l'approximation normale
        # habituelle du maximum de vraisemblance.
        manquantes = comparaison["p"].isna() & comparaison["z"].notna()
        comparaison.loc[manquantes, "p"] = 2 * norm.sf(
            comparaison.loc[manquantes, "z"].abs()
        )
        comparaison.to_csv(TABLEAUX / "03_comparaison_modeles.csv", index=False)

        pd.DataFrame([
            {"parametre": "rho (décalage spatial, M2)", "valeur": rho},
            {"parametre": "lambda (erreur spatiale, M3)", "valeur": lambda_},
            {"parametre": "R2 intra (M1)", "valeur": resultat_ols.rsquared},
            {"parametre": "Observations", "valeur": len(ordre) * len(annees)},
            {"parametre": "Municipalités", "valeur": len(ordre)},
            {"parametre": "Années", "valeur": len(annees)},
        ]).to_csv(TABLEAUX / "03_parametres_modeles.csv", index=False)

        log("\n" + comparaison.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))

    log("étape 3 terminée")


if __name__ == "__main__":
    main()

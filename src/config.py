"""
Paramètres du projet « Diffusion spatiale du déplacement forcé, Colombie ».

Chaque choix de fenêtre, de seuil ou de matrice de voisinage est déclaré ici et
justifié, parce que le résultat d'un modèle spatial dépend beaucoup plus de la
définition du voisinage que de la méthode d'estimation retenue.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Arborescence
# --------------------------------------------------------------------------

RACINE = Path(__file__).resolve().parents[1]
DATA_BRUT = RACINE / "data" / "raw"
DATA_TRAITE = RACINE / "data" / "processed"
SORTIES = RACINE / "outputs"
FIGURES = SORTIES / "figures"
TABLEAUX = SORTIES / "tables"

for _d in (DATA_TRAITE, FIGURES, TABLEAUX):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Systèmes de coordonnées
# --------------------------------------------------------------------------

CRS_SOURCE = "EPSG:4326"

# MAGNA-SIRGAS / Origen Nacional, la projection officielle colombienne pour les
# travaux à l'échelle du pays. Les surfaces et les distances de voisinage sont
# calculées dans ce système.
CRS_METRIQUE = "EPSG:9377"

# --------------------------------------------------------------------------
# Fenêtre du panel
# --------------------------------------------------------------------------

# Le registre unique des victimes remonte à 1985, mais la déclaration
# rétrospective rend les années antérieures à 2000 peu comparables : beaucoup de
# faits anciens ont été enregistrés tardivement, ce qui écrase la chronologie.
ANNEE_DEBUT = 2000

# 2023 est écarté : l'extraction s'arrête en août, l'année est tronquée et son
# inclusion produirait une chute artificielle en fin de période.
ANNEE_FIN = 2022

# --------------------------------------------------------------------------
# Variables construites à partir du registre
# --------------------------------------------------------------------------

# Libellés exacts du champ HECHO dans le fichier source. Ils servent de clés :
# une faute de frappe ici produit silencieusement une colonne de zéros, d'où le
# contrôle d'existence à l'étape 1.
HECHO_DEPLACEMENT = "Desplazamiento forzado"

HECHOS_VIOLENCE_LETALE = [
    "Homicidio",
    "Desaparición forzada",
]

HECHOS_INTIMIDATION = [
    "Amenaza",
]

HECHOS_COMBAT = [
    "Acto terrorista / Atentados / Combates / Enfrentamientos / Hostigamientos",
    "Minas Antipersonal, Munición sin Explotar y Artefacto Explosivo improvisado",
]

# --------------------------------------------------------------------------
# Matrice de voisinage
# --------------------------------------------------------------------------

# Le voisinage principal est celui des k plus proches voisins. Ce choix est
# dicté par la géographie colombienne : la contiguïté simple laisse San Andrés y
# Providencia sans voisin, et un îlot sans voisin rend la matrice de poids non
# inversible dans les modèles à décalage spatial. Les k plus proches voisins
# garantissent que chaque municipalité en a exactement k.
#
# k = 5 correspond à l'ordre de grandeur du nombre de voisins contigus d'une
# municipalité colombienne moyenne, ce qui rend les deux définitions comparables.
K_VOISINS = 5

# La contiguïté de type reine sert de test de robustesse : deux municipalités
# sont voisines si elles partagent au moins un point de frontière.
UTILISER_REINE_EN_ROBUSTESSE = True

# --------------------------------------------------------------------------
# Analyse exploratoire
# --------------------------------------------------------------------------

# Nombre de permutations pour l'inférence des statistiques de Moran. 999 est le
# standard qui donne une précision suffisante sur un seuil à 5 %.
PERMUTATIONS = 999

SEUIL_SIGNIFICATIVITE = 0.05

# Années cartographiées en LISA. Elles ne sont pas prises au hasard :
# 2002 est le pic historique du déplacement, 2008 suit la démobilisation des
# groupes paramilitaires, 2013 se situe pendant les négociations de La Havane,
# 2022 est la dernière année complète disponible.
ANNEES_LISA = [2002, 2008, 2013, 2022]

# --------------------------------------------------------------------------
# Modélisation
# --------------------------------------------------------------------------

# Les variables explicatives entrent décalées d'un an. La raison est de fond :
# une menace et un déplacement enregistrés la même année dans la même
# municipalité décrivent souvent le même épisode, et les régresser l'un sur
# l'autre mesurerait une identité comptable plutôt qu'un enchaînement. Le
# décalage ne règle pas la simultanéité, il la réduit ; l'analyse reste
# descriptive et prédictive, elle n'identifie pas d'effet causal.
DECALAGE_ANNEES = 1

# Transformation de la variable dépendante. Le sinus hyperbolique inverse se
# comporte comme un logarithme pour les grandes valeurs tout en étant défini en
# zéro, ce qui compte ici : une majorité de municipalités-années sont à zéro.
TRANSFORMATION = "asinh"

# --------------------------------------------------------------------------
# Rendu
# --------------------------------------------------------------------------

DPI_FIGURES = 200

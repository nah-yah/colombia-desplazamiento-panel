# Diffusion spatiale du déplacement forcé en Colombie, 2000-2022

# Spatial Diffusion of Forced Displacement in Colombia, 2000-2022

---

## Français

### Contexte

L'Observatoire territorial pour la stabilisation (OTE) est un centre d'analyse
fictif qui appuie la programmation territoriale des politiques de
stabilisation. Son mandat porte sur une question d'allocation.

Les enveloppes de stabilisation sont réparties municipalité par municipalité.
Cette unité d'allocation n'a de sens que si les phénomènes qu'elle vise
s'arrêtent aux limites communales. Si le déplacement forcé se diffuse d'une
municipalité à ses voisines, alors traiter une municipalité isolément revient à
financer une partie seulement du problème, et à laisser le reste se reformer
juste à côté.

Le projet est un cas d'école : le commanditaire et son mandat sont inventés,
toutes les données sont réelles et publiques.

### Question

Le déplacement forcé se diffuse-t-il entre municipalités voisines au-delà de ce
qu'expliquent les violences locales, et quelle part d'un choc local ne reste pas
local ?

### Données

| Source | Jeu | Couverture | Licence |
|---|---|---|---|
| Unité pour les victimes (UARIV) | Registre unique des victimes, faits victimisants | 691 373 lignes, municipalité et mois, 1985 à août 2023 | CC BY |
| OCHA COD-AB | Limites municipales | 1 122 municipalités, millésime 2020 | CC BY |
| OCHA COD-PS | Population municipale projetée | 2024 | CC BY |
| SIDIH / ONUDC | Cultures de coca | 2001 à 2013, annexe seulement | CC BY |

Le portail national `datos.gov.co` refuse les requêtes automatisées. Toutes les
sources passent donc par le catalogue humanitaire HDX, qui en republie une copie
stable et citable. Le détail est dans [data/README_data.md](data/README_data.md).

### Construction du panel

Le panel est complété : une municipalité-année absente du registre signifie zéro
victime enregistrée, pas une donnée manquante. Laisser ces cases vides ferait
disparaître des observations et tirerait toute moyenne vers le haut. La grille
est donc reconstruite et comblée par des zéros. 16,3 % des municipalité-années
sont à zéro déplacement.

Les codes DIVIPOLA sont normalisés sur cinq caractères avant tout rapprochement,
le fichier source les stockant en numérique, ce qui a fait perdre le zéro
initial des départements 05 et 08. Chaque ligne écartée est comptée et le motif
journalisé dans `outputs/tables/01_journal_nettoyage.csv` : 2 164 lignes sans
municipalité, 49 codes non conformes, six codes du registre sans géométrie
correspondante soit 0,03 % des victimes. Une municipalité, Mapiripana en
Guainía, est exclue faute de population au dénominateur.

Panel final : 1 121 municipalités × 23 années = 25 783 observations, équilibré.

Le dénominateur de population est celui de 2024, unique pour toute la période.
Dans un modèle à effets fixes municipaux et variable dépendante en logarithme,
un dénominateur constant dans le temps est entièrement absorbé par l'effet fixe
et ne modifie aucun coefficient. Il n'affecte que les cartes descriptives, où le
choix est signalé.

### Méthode

**Voisinage.** La matrice principale est celle des cinq plus proches voisins,
calculée sur les centroïdes projetés en MAGNA-SIRGAS. Ce choix est dicté par la
géographie : la contiguïté simple laisse San Andrés y Providencia sans voisin, et
une ligne vide rend la matrice non inversible dans un modèle à décalage spatial.
La contiguïté de type reine sert de contrôle ; les deux séries d'indices de Moran
sont corrélées à 0,96.

**Transformation.** Le sinus hyperbolique inverse est retenu plutôt que
`log(1 + x)` : il se comporte comme un logarithme aux valeurs élevées, reste
défini en zéro, ce qui compte quand une observation sur six est nulle, et dépend
moins de l'unité choisie.

**Décalage.** Les variables explicatives entrent décalées d'un an. Une menace et
un déplacement enregistrés la même année dans la même municipalité décrivent
souvent le même épisode ; les régresser l'un sur l'autre mesurerait une identité
comptable. Le décalage réduit la simultanéité sans la supprimer.

**Trois modèles**, dans cet ordre : effets fixes à deux voies sans terme spatial
(M1), décalage spatial de la variable dépendante (M2), erreur spatialement
autocorrélée (M3). Les effets d'année sont retirés en amont, avant que spreg
n'absorbe les effets municipaux, ce qui revient à une estimation à deux voies.
Sans cette étape, la chute nationale du déplacement après 2016 serait attribuée
à la dépendance spatiale : toutes les municipalités baissant ensemble, chacune
ressemble à ses voisines.

**Diagnostic.** L'indice de Moran est calculé sur les résidus de M1 plutôt que
par les tests du multiplicateur de Lagrange pour panel, dont l'implémentation
dans `spreg` construit une matrice pleine de 24 662², soit 4,5 Go. Le Moran des
résidus répond à la même question et se lit directement.

### Résultats

#### Le déplacement est un phénomène de grappes, et il l'est resté

L'indice de Moran de la variable dépendante reste compris entre 0,60 et 0,73 sur
les vingt-trois années, significatif dans les vingt-trois. Le volume s'effondre
entre 2002 (838 000 victimes) et 2020 (108 000), puis remonte à 291 000 en 2022
avec la recomposition des groupes armés. La structure spatiale, elle, tient.
L'accord de paix de 2016 n'y laisse aucune trace.

Les indicateurs locaux confirment cette stabilité : le nombre de municipalités
en grappe haute passe de 179 en 2002 à 177 en 2022, avec un maximum de 207 en
2013.

54 municipalités appartiennent à une grappe haute sur les quatre années
examinées : Caquetá (13), Antioquia, Chocó, Meta, Norte de Santander et
Putumayo (6 chacun), Bolívar et Cauca (3), Córdoba et Guaviare (2), Nariño (1).
C'est la géographie structurelle du déplacement colombien, et elle recoupe les
zones d'économie illicite et de faible présence de l'État.

#### Les violences locales n'épuisent pas la structure spatiale

| Modèle | Violence létale | Menaces | Combats | Paramètre spatial | AIC |
|---|---|---|---|---|---|
| M1 effets fixes | 0,447 | 0,510 | 0,105 | — | — |
| M2 décalage spatial | 0,274 | 0,335 | 0,057 | ρ = 0,549 | 293 713 |
| M3 erreur spatiale | 0,277 | 0,334 | 0,077 | λ = 0,586 | 294 681 |

Tous les coefficients sont significatifs à 1 ‰. Les écarts types de M1 sont
groupés par municipalité.

Le Moran des résidus de M1 vaut 0,294 en médiane et reste significatif dans les
vingt-deux années estimées. Une fois retirés les effets fixes et les violences
locales décalées, ce qui reste est encore fortement groupé dans l'espace, signe
que le modèle non spatial est mal spécifié.

L'ajout du terme spatial fait chuter les coefficients de près de 40 %. Une part
substantielle de ce que M1 attribuait aux violences locales était en réalité de
la dépendance entre voisines. Le décalage spatial l'emporte sur l'erreur
spatiale au critère d'information.

#### 52 % de l'effet se produit hors de la municipalité touchée

| Variable | Effet direct | Effet indirect | Effet total |
|---|---|---|---|
| Violence létale, décalée d'un an | 0,293 | 0,315 | 0,608 |
| Menaces, décalées d'un an | 0,358 | 0,386 | 0,744 |
| Combats et engins explosifs, décalés | 0,060 | 0,065 | 0,125 |

Un choc de violence dans une municipalité produit un peu plus de la moitié de
son effet total ailleurs que là où il a lieu. C'est la réponse à la question
posée en tête.

La part déversée est identique pour les trois variables, et ce n'est pas une
erreur de calcul : dans un modèle à décalage spatial, le rapport de l'effet
indirect à l'effet total ne dépend que de ρ et du voisinage, jamais du
coefficient de la variable. Le paramètre spatial décrit la géographie de la
diffusion, commune à tous les chocs, et les coefficients en décrivent
l'intensité.

Pour l'allocation des ressources, financer une municipalité isolément revient à
ne traiter que la moitié de l'effet d'un choc. Les 54 municipalités en grappe
persistante, et les grappes auxquelles elles appartiennent, sont les unités
d'intervention pertinentes : elles décrivent une géographie du déplacement qui
n'a pas bougé en vingt ans.

### Ce que cette analyse ne dit pas

Aucun effet causal n'est identifié. Les faits de violence et le déplacement sont
enregistrés par la même administration, à partir des mêmes déclarations, et le
décalage d'un an ne les rend pas exogènes. Le modèle décrit une structure de
dépendance, il ne dit pas par quel mécanisme le déplacement se propage.

Le registre est administratif et non épidémiologique. Il compte les personnes
reconnues victimes, ce qui dépend de leur déclaration et de son traitement. Les
zones où l'État est le plus absent sont vraisemblablement celles où la
sous-déclaration est la plus forte, ce qui joue contre les résultats observés
plutôt qu'en leur faveur.

Les frontières municipales sont figées au millésime 2020, alors que la Colombie
en a créé quelques-unes sur la période. Six codes du registre restent sans
géométrie, pour 0,03 % des victimes.

La coca n'entre pas dans les modèles. Le jeu SIDIH s'arrête en 2013 et ses
totaux nationaux valent environ trois fois les chiffres publiés par l'ONUDC. Un
facteur d'échelle constant serait absorbé par les effets fixes, mais la série
tronquée aurait imposé de réduire le panel de dix ans. L'arbitrage est documenté
dans [data/README_data.md](data/README_data.md).

Un modèle de Durbin spatial, qui ajouterait les variables explicatives décalées,
permettrait des parts déversées distinctes par variable. Il n'est pas estimé
ici.

### Reproduire

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
python run_all.py
```

Comptez une vingtaine de minutes, sources déjà téléchargées : sept pour la
lecture du registre et l'assemblage du panel, six pour l'étape 2, où l'inférence
de Moran repose sur 999 permutations par année répétées pour deux définitions du
voisinage. `python run_all.py --depuis 2` reprend après la construction du
panel.

### Arborescence

```
data/raw/              sources téléchargées, non versionnées (environ 180 Mo)
data/processed/        panel, géométries, voisinages, LISA
src/config.py          tous les paramètres, avec justification
src/p01 à p04          les quatre étapes de la chaîne
outputs/figures/       6 cartes et graphiques
outputs/tables/        14 tableaux de résultats
notebooks/analyse.ipynb
```

---

## English

### Context

The Territorial Observatory for Stabilisation (OTE) is a fictional policy
analysis centre. Stabilisation budgets in Colombia are allocated municipality by
municipality. That unit only makes sense if the phenomena it targets stop at
municipal boundaries. If forced displacement diffuses to neighbours, funding one
municipality in isolation treats only part of the problem and lets the rest
re-form next door.

The commissioning body is invented; every dataset is real and public.

### Question

Does forced displacement diffuse between neighbouring municipalities beyond what
local violence explains, and what share of a local shock does not stay local?

### Method

A balanced panel of 1,121 municipalities × 23 years (25,783 observations) is
built from the Colombian victims' registry. Absent municipality-years mean zero
recorded victims, not missing data, so the grid is completed with zeros; 16.3 %
of cells are zero. Every dropped row is logged with its reason.

The outcome is the inverse hyperbolic sine of the displacement rate, which
behaves like a log at high values while remaining defined at zero. Regressors
enter lagged one year. Spatial weights are five nearest neighbours on projected
centroids, since queen contiguity leaves San Andrés without a neighbour and an
empty row makes the weights matrix non-invertible in a lag model. The two Moran
series correlate at 0.96.

Three specifications: two-way fixed effects (M1), spatial lag (M2), spatial error
(M3). Year effects are removed before spreg absorbs municipal effects, giving a
two-way estimate. Without this step the post-2016 national decline would be read
as spatial dependence.

### Key findings

Displacement is a cluster phenomenon and has stayed one. Global Moran's I on the
outcome stays between 0.60 and 0.73 across all 23 years, significant in every
one. Volume collapses from 838,000 victims in 2002 to 108,000 in 2020 then
rebounds to 291,000 in 2022, while the spatial structure holds. The 2016 peace
accord leaves no trace in it. 54 municipalities sit in a high-high cluster in all
four mapped years, concentrated in Caquetá, Antioquia, Chocó, Meta, Norte de
Santander and Putumayo.

Local violence does not exhaust the spatial structure. Moran's I on M1 residuals
is 0.294 at the median and significant in all 22 estimated years, so the
non-spatial model is misspecified. Adding the spatial lag cuts the coefficients
by roughly 40 % (lethal violence 0.447 to 0.274), and the lag model beats the
error model on AIC (ρ = 0.549, λ = 0.586).

52 % of the effect occurs outside the municipality hit. Decomposing the lag
model, a violence shock produces slightly more than half its total effect
elsewhere. The spillover share is identical across variables by construction: in
a lag model the indirect-to-total ratio depends only on ρ and the weights, never
on the coefficient. Funding a municipality in isolation therefore addresses about
half of a shock's effect, and the persistent clusters are the relevant
intervention units.

### Caveats

No causal effect is identified. Violence and displacement are recorded by the
same administration from the same declarations, and a one-year lag does not make
them exogenous. The registry is administrative rather than epidemiological, and
under-reporting is likely worst where the state is most absent, which works
against the observed results rather than for them. Municipal boundaries are
frozen at the 2020 vintage. Coca is excluded from the models: the available
series stops in 2013 and its national totals are about three times UNODC's
published figures.

### Reproduce

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
python run_all.py
```

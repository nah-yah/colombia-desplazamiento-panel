# Données du projet

Aucun fichier de `data/` n'est versionné : la chaîne les reconstruit à
l'identique depuis les catalogues d'origine.

```
python src/telecharger_donnees.py
```

Environ 180 Mo, dont 117 Mo pour les seules limites administratives.

## Sources

| Source | Jeu | Fichier attendu | Catalogue |
|---|---|---|---|
| Unité pour les victimes (UARIV) | Registre unique, faits victimisants | `hechos_victimizantes.csv` | [HDX](https://data.humdata.org/dataset/colombia-hechos-victimizantes-uariv) |
| OCHA COD-AB | Limites administratives, niveaux 0 à 2 | `col_admin_shapefiles.zip` | [HDX](https://data.humdata.org/dataset/cod-ab-col) |
| OCHA COD-PS | Population municipale projetée 2024 | `col_admpop_adm2_2024.csv` | [HDX](https://data.humdata.org/dataset/cod-ps-col) |
| SIDIH / ONUDC | Cultures de coca par municipalité | `sidih_coca.csv` | [HDX](https://data.humdata.org/dataset/sidih-cultivos-de-coca) |

## Pourquoi HDX plutôt que le portail national

Le portail colombien `datos.gov.co` répond `403 Forbidden` à toute requête
automatisée, y compris avec un agent utilisateur de navigateur, sur son
interface Socrata comme sur ses liens de téléchargement direct. Les jeux sont
donc pris sur le catalogue humanitaire HDX, qui republie les mêmes données sous
forme de copies stables, versionnées et citables.

## Quatre limites qui changent la lecture des résultats

### 1. Le registre compte des personnes reconnues, pas des événements

Le registre unique des victimes recense les personnes dont le statut de victime
a été reconnu par l'administration, rattachées à la municipalité où le fait
s'est produit. Le décompte dépend donc de deux étapes administratives : la
personne doit avoir déclaré, et sa déclaration doit avoir été traitée.

La sous-déclaration est vraisemblablement la plus forte là où l'État est le plus
absent, c'est-à-dire dans les zones qui ressortent déjà comme les plus touchées.
Le biais joue **contre** les résultats de l'analyse : avec une couverture
homogène, les grappes identifiées ressortiraient au moins autant.

Le fichier est arrêté en août 2023, ce qui rend 2023 incomplète. L'année est
exclue de la fenêtre.

### 2. Les codes DIVIPOLA perdent leur zéro initial

Le fichier source stocke les codes de municipalité en numérique. Antioquia (05)
et Atlántico (08) y apparaissent donc sur quatre caractères. Tout rapprochement
avec les limites administratives est précédé d'une normalisation sur cinq
caractères. Sans cette étape, 127 174 lignes ne trouveraient pas leur géométrie
et deux départements entiers seraient absents de l'analyse, sans message
d'erreur.

Le journal de nettoyage complet est écrit dans
`outputs/tables/01_journal_nettoyage.csv`.

### 3. Le dénominateur de population est unique pour toute la période

DANE publie des projections municipales annuelles, mais le fichier COD-PS
diffusé sur HDX ne couvre que les millésimes récents. Le taux pour mille est
donc calculé avec la population 2024 sur toutes les années.

Ce choix est sans conséquence sur les modèles : la variable dépendante est en
transformation logarithmique et les effets fixes municipaux absorbent un
dénominateur constant dans le temps. Aucun coefficient n'en est affecté. Il
affecte en revanche les cartes descriptives, où les taux des années 2000 sont
mécaniquement sous-estimés par rapport à une population d'époque plus faible. La
mention figure sur les figures concernées.

Une municipalité, Mapiripana en Guainía, porte une population nulle dans le
fichier source. Elle est exclue de l'échantillon, sans correction par une valeur
plancher.

### 4. Les cultures de coca ne sont pas utilisées dans les modèles

Le jeu SIDIH a été téléchargé et examiné, puis écarté des spécifications pour
deux raisons.

La couverture d'abord : la série s'arrête en 2013. L'inclure aurait imposé de
ramener le panel de 23 à 13 années, donc de perdre toute la période
post-accord de paix, celle où se pose la question de la recomposition
territoriale.

La cohérence des niveaux ensuite : les totaux nationaux du jeu valent environ
trois fois les chiffres de recensement publiés par l'ONUDC, avec un facteur
stable dans le temps (3,00 en 2001, 2,94 en 2007, 3,01 en 2013). Un facteur
d'échelle constant serait absorbé par des effets fixes en logarithme, si bien
que la variation spatiale et temporelle resterait exploitable. Vérifier l'écart
de niveau avant de publier une variable étiquetée « hectares » dépasse le cadre
de ce travail.

Le fichier reste téléchargé et documenté pour une analyse sur la sous-période.

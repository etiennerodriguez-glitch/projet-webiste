"""Outils de modélisation pour le value betting.

- Football : Poisson / Dixon-Coles sur des xG attendus, Elo -> 1X2, marché sans marge.
- Basket : écart de points attendu -> probabilité (loi normale).
- Combinaison pondérée des sources, cote juste, EV, mise de Kelly.

Usage : python3 modele/value.py  (lance les calculs du fichier analyses_du_jour.py)
"""

from math import erf, exp, factorial, sqrt

MAX_BUTS = 10


def poisson(k, lam):
    return lam ** k * exp(-lam) / factorial(k)


def tau(x, y, lam, mu, rho):
    """Correction Dixon-Coles des scores faibles."""
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    if x == 0 and y == 1:
        return 1 + lam * rho
    if x == 1 and y == 0:
        return 1 + mu * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def matrice_scores(lam, mu, rho=-0.10):
    m = [[tau(x, y, lam, mu, rho) * poisson(x, lam) * poisson(y, mu)
          for y in range(MAX_BUTS + 1)] for x in range(MAX_BUTS + 1)]
    total = sum(map(sum, m))
    return [[p / total for p in ligne] for ligne in m]


def marches_foot(lam, mu, rho=-0.10):
    """Probabilités des marchés principaux à partir des buts attendus dom./ext."""
    m = matrice_scores(lam, mu, rho)
    rng = range(MAX_BUTS + 1)
    p1 = sum(m[x][y] for x in rng for y in rng if x > y)
    px = sum(m[x][x] for x in rng)
    p2 = 1 - p1 - px
    over25 = sum(m[x][y] for x in rng for y in rng if x + y >= 3)
    over35 = sum(m[x][y] for x in rng for y in rng if x + y >= 4)
    btts = sum(m[x][y] for x in range(1, MAX_BUTS + 1) for y in range(1, MAX_BUTS + 1))
    return {
        "1": p1, "X": px, "2": p2,
        "1X": p1 + px, "X2": px + p2, "12": p1 + p2,
        "+2.5": over25, "-2.5": 1 - over25,
        "+3.5": over35, "-3.5": 1 - over35,
        "BTTS oui": btts, "BTTS non": 1 - btts,
        "1 & +1.5": sum(m[x][y] for x in rng for y in rng if x > y and x + y >= 2),
        "1 (-1.5)": sum(m[x][y] for x in rng for y in rng if x - y >= 2),
        "2 (-1.5)": sum(m[x][y] for x in rng for y in rng if y - x >= 2),
    }


def elo_1x2(elo_dom, elo_ext, avantage_dom=65, nul_base=0.27):
    """Elo club -> 1X2. La part de nul décroît avec l'écart de niveau."""
    dr = elo_dom + avantage_dom - elo_ext
    we = 1 / (1 + 10 ** (-dr / 400))
    p_nul = max(0.12, nul_base - 0.00028 * abs(dr))
    p1 = we - p_nul / 2
    p2 = 1 - we - p_nul / 2
    if p2 < 0.02:
        p2 = 0.02
        p1 = 1 - p_nul - p2
    if p1 < 0.02:
        p1 = 0.02
        p2 = 1 - p_nul - p1
    return {"1": p1, "X": p_nul, "2": p2,
            "1X": p1 + p_nul, "X2": p_nul + p2, "12": p1 + p2}


def sans_marge(cotes):
    """Retire la marge par la méthode de Shin simplifiée (puissance)."""
    inv = [1 / c for c in cotes]
    lo, hi = 0.5, 3.0
    for _ in range(100):
        k = (lo + hi) / 2
        s = sum(p ** k for p in inv)
        if s > 1:
            lo = k
        else:
            hi = k
    return [p ** k for p in inv]


def marge(cotes):
    return sum(1 / c for c in cotes) - 1


def phi(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def basket_proba(ecart_attendu, ligne=0.0, ecart_type=12.5):
    """P(équipe couvre `ligne`) si elle gagne en moyenne de `ecart_attendu` points.
    ligne=0 -> victoire ; ligne=-5.5 -> victoire par 6+ points."""
    return 1 - phi((-ligne - ecart_attendu) / ecart_type)


def total_proba_over(total_attendu, ligne, ecart_type=18.0):
    return 1 - phi((ligne - total_attendu) / ecart_type)


def melange(sources):
    """sources = [(poids, proba), ...] -> proba pondérée."""
    poids = sum(w for w, _ in sources)
    return sum(w * p for w, p in sources) / poids


def ev(p, cote):
    return p * cote - 1


def kelly(p, cote, fraction=0.25):
    b = cote - 1
    f = (b * p - (1 - p)) / b
    return max(0.0, f * fraction)


def combine(selections):
    """selections = [(libelle, proba, cote)] supposées indépendantes."""
    p, c = 1.0, 1.0
    for _, pi, ci in selections:
        p *= pi
        c *= ci
    return p, c, ev(p, c)

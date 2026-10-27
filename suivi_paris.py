#!/usr/bin/env python3
"""Suivi de la bankroll à partir de paris_30e.csv.

Usage : python3 suivi_paris.py [chemin_csv]

Colonne `resultat` : "gagne", "perdu", "rembourse" ou "en attente".
Le gain/perte et la bankroll après chaque pari sont recalculés dans l'ordre du fichier.
"""
import csv
import sys
from collections import defaultdict

BANKROLL_DEPART = 30.0
COLONNES = ["date", "sport", "match", "pari", "cote", "cote_juste", "proba_estimee",
            "confiance", "mise_eur", "resultat", "gain_perte_eur", "bankroll_apres"]


def charger(chemin):
    try:
        with open(chemin, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def recalculer(lignes):
    bankroll = BANKROLL_DEPART
    for l in lignes:
        mise, cote = float(l["mise_eur"]), float(l["cote"])
        res = l["resultat"].strip().lower()
        if res == "gagne":
            gp = round(mise * (cote - 1), 2)
        elif res == "perdu":
            gp = -mise
        elif res == "rembourse":
            gp = 0.0
        else:
            l["gain_perte_eur"], l["bankroll_apres"] = "", ""
            continue
        bankroll = round(bankroll + gp, 2)
        l["gain_perte_eur"], l["bankroll_apres"] = f"{gp:.2f}", f"{bankroll:.2f}"
    return bankroll


def bilan(lignes, bankroll):
    regles = [l for l in lignes if l["resultat"].strip().lower() in ("gagne", "perdu", "rembourse")]
    mises = sum(float(l["mise_eur"]) for l in regles)
    benef = bankroll - BANKROLL_DEPART
    print(f"Bankroll actuelle : {bankroll:.2f} €")
    print(f"Bénéfice/perte depuis le départ : {benef:+.2f} €")
    print(f"ROI : {benef / mises * 100:+.1f} %" if mises else "ROI : n/a (aucun pari réglé)")
    par_sport = defaultdict(lambda: [0, 0])
    for l in regles:
        if l["resultat"].strip().lower() == "rembourse":
            continue
        par_sport[l["sport"]][1] += 1
        par_sport[l["sport"]][0] += l["resultat"].strip().lower() == "gagne"
    for sport, (g, n) in sorted(par_sport.items()):
        print(f"  {sport} : {g}/{n} ({g / n * 100:.0f} %)")
    attente = [l for l in lignes if l["resultat"].strip().lower() == "en attente"]
    if attente:
        print(f"Paris en attente : {len(attente)} ({sum(float(l['mise_eur']) for l in attente):.2f} € engagés)")


if __name__ == "__main__":
    chemin = sys.argv[1] if len(sys.argv) > 1 else "paris_30e.csv"
    lignes = charger(chemin)
    bankroll = recalculer(lignes)
    if lignes:
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLONNES)
            w.writeheader()
            w.writerows(lignes)
    bilan(lignes, bankroll)

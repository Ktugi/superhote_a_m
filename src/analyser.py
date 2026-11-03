"""Vérifie, sur les données exportées par telecharger.py, les hypothèses
dont dépend envoyer.py.

Hypothèses vérifiées :
1. Chaque avis 5 étoiles porte un code de confirmation, unique.
2. Ce code se retrouve dans le champ external_id de la réservation
   correspondante, qui a le même rental_id que l'avis.
3. Les avis dont la réservation est introuvable sont tous antérieurs
   à la plus ancienne réservation connue de SuperHote : ils datent
   d'avant l'arrivée des réservations dans l'outil.
4. Les réservations portent un prénom, utilisé dans le message.

Usage : python src/telecharger.py, puis python src/analyser.py
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def charger(nom):
    chemin = DATA / nom
    if not chemin.exists():
        print(f"{chemin} introuvable : lancez d'abord src/telecharger.py.",
              file=sys.stderr)
        sys.exit(1)
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def analyser_avis(avis):
    avis_5 = [a for a in avis if a.get("rating") == 5]
    codes = [a.get("reservation_confirmation_code") for a in avis_5]
    codes = [c for c in codes if c]
    sans_date = sum(1 for a in avis if not a.get("reviewed_at"))

    print("--- Avis ---")
    print("avis au total           :", len(avis))
    print("avis 5 étoiles          :", len(avis_5))
    print("  dont avec un code     :", len(codes))
    print("  codes distincts       :", len(set(codes)))
    print("avis sans date          :", sans_date)
    return avis_5


def analyser_correspondance(avis_5, reservations):
    par_code = {r.get("external_id"): r for r in reservations if r.get("external_id")}
    trouves, non_trouves, logement_different = [], [], 0
    for a in avis_5:
        resa = par_code.get(a.get("reservation_confirmation_code"))
        if resa is None:
            non_trouves.append(a)
            continue
        trouves.append(a)
        if resa.get("rental_id") != a.get("rental_id"):
            logement_different += 1

    print("--- Correspondance avis 5 étoiles -> réservation ---")
    print("retrouvés               :", len(trouves))
    print("non retrouvés           :", len(non_trouves))
    print("  rental_id différent   :", logement_different)

    if non_trouves:
        plus_ancienne = min(r["created_at"] for r in reservations if r.get("created_at"))
        anterieurs = sum(1 for a in non_trouves
                         if (a.get("reviewed_at") or "") < plus_ancienne)
        print("non retrouvés antérieurs à la plus ancienne réservation :",
              f"{anterieurs}/{len(non_trouves)}")


def analyser_reservations(reservations):
    if not reservations:
        print("--- Réservations --- aucune")
        return
    avec_prenom = sum(1 for r in reservations
                      if isinstance(r.get("guest_first_name"), str)
                      and r["guest_first_name"].strip())
    print("--- Réservations ---")
    print("réservations au total   :", len(reservations))
    print("avec un prénom          :", avec_prenom)
    print("champs d'une réservation:", list(reservations[0].keys()))


if __name__ == "__main__":
    avis = charger("avis.json")
    reservations = charger("reservations.json")
    avis_5 = analyser_avis(avis)
    analyser_correspondance(avis_5, reservations)
    analyser_reservations(reservations)
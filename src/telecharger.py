import json
import sys
from pathlib import Path

from client import charger_token, lister_tout

DATA = Path(__file__).resolve().parent.parent / "data"


def sauver(nom, donnees):
    with open(DATA / nom, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    token = charger_token()

    avis = lister_tout(token, "/reviews", "reviews")
    if avis is None:
        sys.exit(1)
    sauver("avis.json", avis)
    print("avis :", len(avis))

    reservations = lister_tout(token, "/reservations", "reservations")
    if reservations is None:
        sys.exit(1)
    sauver("reservations.json", reservations)
    print("réservations :", len(reservations))






import sys

from client import appeler, charger_token, envoyer_message
from envoyer import charger_message, composer

#NECESSITE LA CREATION FICTIVE D'UNE RESERVATION TEST SUR SUPERHOTE 

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python src/tester_envoi.py ID_RESERVATION", file=sys.stderr)
        sys.exit(1)
    reservation_id = sys.argv[1]

    token = charger_token()
    reponse = appeler(token, f"/reservations/{reservation_id}")
    if reponse is None or reponse.status_code != 200:
        print("Réservation introuvable ou erreur de lecture.", file=sys.stderr)
        sys.exit(1)
    try:
        resa = reponse.json().get("result", {})
    except ValueError:
        print("Réponse non JSON.", file=sys.stderr)
        sys.exit(1)
    if isinstance(resa, dict) and isinstance(resa.get("reservation"), dict):
        resa = resa["reservation"]

    print("Prénom   :", resa.get("guest_first_name"))
    print("Plateforme :", resa.get("platform_name"))
    print("Séjour   :", resa.get("checkin"), "->", resa.get("checkout"))
    if input("Envoyer un SMS de test à cette réservation ? (oui/non) ") != "oui":
        print("Annulé.")
        sys.exit(0)

    prenom=resa.get("guest_first_name")
    modele=charger_message()
    texte=composer(modele,prenom)
    resultat = envoyer_message(token, reservation_id, texte)
    print("Résultat :", resultat)
    sys.exit(0 if resultat == "envoye" else 1)

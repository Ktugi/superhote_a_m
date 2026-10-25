import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from client import charger_token, envoyer_message, lister_tout

PARIS = ZoneInfo("Europe/Paris")
FICHIER_ETAT = Path(__file__).resolve().parent.parent / "data" / "etat.json"
FENETRE_JOURS = 45   # recherche de la réservation : jours avant l'avis
MAX_ENVOIS = 20      # garde-fou : au-delà, le script refuse d'envoyer

# À adapter avec le client. {salut} devient "Bonjour Marie," ou "Bonjour,"
FICHIER_MESSAGE = FICHIER_ETAT.parent / "message.txt"
LONGUEUR_MAX = 1000   # protection contre un fichier collé par erreur


def charger_message():
    """Lit data/message.txt. Rend le texte, ou None s'il est inutilisable."""
    if not FICHIER_MESSAGE.exists():
        print("data/message.txt est introuvable.", file=sys.stderr)
        return None
    try:
        texte = FICHIER_MESSAGE.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        print("data/message.txt n'est pas en texte brut. Dans TextEdit : "
              "Format > Convertir au format Texte.", file=sys.stderr)
        return None
    if texte.startswith("{\\rtf"):
        print("data/message.txt est en texte enrichi. Dans TextEdit : "
              "Format > Convertir au format Texte.", file=sys.stderr)
        return None
    if not texte:
        print("data/message.txt est vide.", file=sys.stderr)
        return None
    if len(texte) > LONGUEUR_MAX:
        print(f"data/message.txt dépasse {LONGUEUR_MAX} caractères.",
              file=sys.stderr)
        return None
    return texte


def composer(modele, prenom):
    if prenom:
        return modele.replace("{prenom}", prenom)
    return modele.replace(" {prenom}", "").replace("{prenom}", "")


# ---------- mémoire des avis traités ----------

def lire_etat():
    if not FICHIER_ETAT.exists():
        return None
    try:
        with open(FICHIER_ETAT, "r", encoding="utf-8") as f:
            etat = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("data/etat.json est illisible (erreur de format). Remettez la "
              "copie etat.json.bak, ou corrigez le fichier.", file=sys.stderr)
        sys.exit(1)
    if not isinstance(etat, dict):
        print("data/etat.json a un contenu inattendu.", file=sys.stderr)
        sys.exit(1)
    etat.setdefault("traites", {})
    return etat


def ecrire_etat(etat):
    """Écriture atomique : un plantage ne peut pas laisser un fichier à moitié écrit."""
    tmp = FICHIER_ETAT.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(etat, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, FICHIER_ETAT)


def initialiser():
    if FICHIER_ETAT.exists():
        print("etat.json existe déjà : rien n'a été modifié.", file=sys.stderr)
        return 1
    etat = {"depart": datetime.now(timezone.utc).isoformat(), "traites": {}}
    ecrire_etat(etat)
    print("Initialisé. Date de départ :", etat["depart"])
    return 0


# ---------- règles d'éligibilité ----------

def lire_date(texte):
    try:
        d = datetime.fromisoformat(texte)
    except (TypeError, ValueError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def date_paris(dt):
    return dt.astimezone(PARIS).date()


def avis_a_traiter(avis_liste, etat, aujourdhui, depart):
    """5 étoiles, avec code, après la date de départ, pas déjà traité,
    et daté d'avant aujourd'hui (heure de Paris)."""
    resultat = []
    for avis in avis_liste:
        if avis.get("rating") != 5 or avis.get("id") is None:
            continue
        if not avis.get("reservation_confirmation_code"):
            continue
        quand = lire_date(avis.get("reviewed_at"))
        if quand is None or quand < depart:
            continue
        if str(avis["id"]) in etat["traites"]:
            continue
        if date_paris(quand) >= aujourdhui:
            continue
        resultat.append((quand, avis))
    resultat.sort(key=lambda couple: couple[0])   # du plus ancien au plus récent
    return [avis for _, avis in resultat]


def trouver_reservation(token, avis):
    """Rend (reservation ou None, lecture_ok)."""
    code = avis["reservation_confirmation_code"].strip().upper()
    jour = date_paris(lire_date(avis["reviewed_at"]))
    params = {
        "rental_id": avis.get("rental_id"),
        "checkout_from": (jour - timedelta(days=FENETRE_JOURS)).isoformat(),
        "checkout_to": (jour + timedelta(days=1)).isoformat(),
    }
    reservations = lister_tout(token, "/reservations", "reservations", params)
    if reservations is None:
        return None, False
    for r in reservations:
        if (r.get("external_id") or "").strip().upper() == code:
            return r, True
    return None, True


# ---------- programme principal ----------

def principal(envoyer, limite):
    etat = lire_etat()
    if etat is None:
        print("Pas de fichier d'état : lance d'abord --init.", file=sys.stderr)
        return 1
    depart = lire_date(etat.get("depart"))
    if depart is None:
        print("Date de départ illisible dans etat.json.", file=sys.stderr)
        return 1

    douteux = [k for k, v in etat["traites"].items()
               if v.get("statut") in ("en_cours", "incertain")]
    if douteux:
        print(f"ATTENTION : {len(douteux)} avis en statut incertain (message "
              "peut-être parti). Vérifie dans SuperHote, puis corrige "
              "data/etat.json.", file=sys.stderr)

    modele = charger_message()
    if modele is None:
        return 1

    print("MODE RÉEL" if envoyer else "MODE SIMULATION (rien n'est envoyé)")
    print("Modèle :", modele)
    print("Date de départ :", etat.get("depart"))

    token = charger_token()
    avis_liste = lister_tout(token, "/reviews", "reviews")
    if avis_liste is None:
        return 1

    aujourdhui = datetime.now(PARIS).date()
    a_traiter = avis_a_traiter(avis_liste, etat, aujourdhui, depart)
    
    total = len(a_traiter)
    a_traiter = a_traiter[:limite or MAX_ENVOIS]
    if total > len(a_traiter):
        print(f"{total} avis éligibles : {len(a_traiter)} traités maintenant, "
              "le reste aux prochains passages.")

    compteurs = {"simule": 0, "envoye": 0, "non_remis": 0, "refuse": 0,
                 "incertain": 0, "introuvable": 0}
    code_sortie = 0

    for avis in a_traiter:                                                                                                                                                                                                                                                                                                                              
        cle = str(avis["id"])
        reservation, lecture_ok = trouver_reservation(token, avis)
        if not lecture_ok:
            code_sortie = 1
            break
        if reservation is None:
            print(f"avis {cle} : réservation introuvable, ignoré (retenté demain)")
            compteurs["introuvable"] += 1
            continue

        prenom = (reservation.get("guest_first_name") or "").strip()
        texte = composer(modele, prenom)

        if not envoyer:
            print(f"[SIMULATION] avis {cle} -> réservation {reservation['id']}, "
                  f"{len(texte)} caractères : {texte}")
            compteurs["simule"] += 1
            continue

        # 1. on note AVANT d'envoyer : un plantage ne pourra jamais provoquer un doublon
        etat["traites"][cle] = {
            "statut": "en_cours",
            "reservation_id": reservation["id"],
            "le": datetime.now(timezone.utc).isoformat(),
        }
        ecrire_etat(etat)

        # 2. envoi unique, sans réessai
        resultat = envoyer_message(token, reservation["id"], texte)

        # 3. on note le résultat
        if resultat == "non_envoye":
            del etat["traites"][cle]       # pas parti : on pourra réessayer
            ecrire_etat(etat)
            code_sortie = 1
            break
        etat["traites"][cle]["statut"] = resultat
        ecrire_etat(etat)
        compteurs[resultat] += 1
        print(f"avis {cle} : {resultat}")
        if resultat == "incertain":
            code_sortie = 1

    detail = " | ".join(f"{k} : {v}" for k, v in compteurs.items() if v)
    print(f"avis lus : {len(avis_liste)} | à traiter : {len(a_traiter)} | {detail}")
    return code_sortie


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SMS aux voyageurs 5 étoiles")
    parser.add_argument("--init", action="store_true",
                        help="crée la mémoire, date de départ = maintenant")
    parser.add_argument("--envoyer", action="store_true",
                        help="envoie vraiment les SMS (sinon simulation)")
    parser.add_argument("--limite", type=int, default=0,
                        help="traite au plus N avis")
    args = parser.parse_args()
    if args.init:
        sys.exit(initialiser())
    sys.exit(principal(args.envoyer, args.limite))

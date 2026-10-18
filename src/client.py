import os
import sys
import time
from pathlib import Path

import keyring
import requests
from dotenv import load_dotenv
from keyring.errors import KeyringError
from requests.exceptions import RequestException

SERVICE = "Projet_avis5_sh"
UTILISATEUR = "api_token"
BASE_URL = "https://connect.superhote.com/api/v2/public"
TIMEOUT = 30
MAX_TENTATIVES = 3
ATTENTE_MAX = 60
MAX_PAGES = 200


def charger_token():
    token = None
    try:
        token = keyring.get_password(SERVICE, UTILISATEUR)
    except KeyringError:
        pass
    if not token:
        chemin_env = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(chemin_env)
        token = os.getenv("SUPERHOTE_TOKEN")
    token = (token or "").strip()
    if not token:
        print("Aucun token trouvé. Vérifie le coffre-fort ou le fichier .env.",
              file=sys.stderr)
        sys.exit(1)
    return token


def _lire_retry_after(reponse):
    try:
        return max(0,int(reponse.headers.get("Retry-After", "")))
    except ValueError:
        return 5


def appeler(token, chemin, params=None):
    """GET avec réessais. Rend la réponse, ou None si on abandonne."""
    url = BASE_URL + chemin
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    for tentative in range(1, MAX_TENTATIVES + 1):
        attente = 2 ** (tentative - 1)  # 1 s, 2 s, 4 s...
        try:
            reponse = requests.get(url, headers=headers, params=params,
                                   timeout=TIMEOUT)
        except RequestException as e:
            print(f"{chemin} : échec réseau ({type(e).__name__}), "
                  f"tentative {tentative}/{MAX_TENTATIVES}", file=sys.stderr)
        else:
            code = reponse.status_code
            if code == 429:
                attente = _lire_retry_after(reponse)
                if attente > ATTENTE_MAX:
                    print(f"{chemin} : 429, attente demandée trop longue "
                          f"({attente} s), abandon", file=sys.stderr)
                    return None
                print(f"{chemin} : 429, nouvel essai dans {attente} s",
                      file=sys.stderr)
            elif code >= 500:
                print(f"{chemin} : erreur serveur {code}, "
                      f"tentative {tentative}/{MAX_TENTATIVES}", file=sys.stderr)
            else:
                return reponse  # succès, ou erreur 4xx qu'on ne réessaie pas
        if tentative < MAX_TENTATIVES:
            time.sleep(attente)
    print(f"{chemin} : abandon après {MAX_TENTATIVES} tentatives",
          file=sys.stderr)
    return None


def _lire_page(token, chemin, params, cle, numero):
    """Rend (liste, last_page) pour une page, ou None en cas de problème."""
    params_page = dict(params)
    params_page["page"] = numero
    reponse = appeler(token, chemin, params_page)
    if reponse is None or reponse.status_code != 200:
        code = "aucune réponse" if reponse is None else reponse.status_code
        print(f"{chemin} page {numero} : échec ({code})", file=sys.stderr)
        return None
    try:
        corps = reponse.json()
    except ValueError:
        print(f"{chemin} page {numero} : réponse non JSON", file=sys.stderr)
        return None
    if not isinstance(corps, dict) or corps.get("success") is not True:
        print(f"{chemin} page {numero} : success absent ou faux",
              file=sys.stderr)
        return None
    result = corps.get("result")
    if not isinstance(result, dict) or not isinstance(result.get(cle), list):
        print(f"{chemin} page {numero} : clé '{cle}' introuvable",
              file=sys.stderr)
        return None
    meta = result.get("meta")
    last_page = meta.get("last_page", 1) if isinstance(meta, dict) else 1
    if not isinstance(last_page, int):
        last_page = 1
    return result[cle], last_page


def lister_tout(token, chemin, cle, params=None):
    """Lit toutes les pages. Rend la liste complète, ou None au premier échec."""
    params = dict(params or {})
    params["per_page"] = 100

    premiere = _lire_page(token, chemin, params, cle, 1)
    if premiere is None:
        return None
    elements, last_page = premiere

    if last_page > MAX_PAGES:
        print(f"{chemin} : {last_page} pages, au-dessus du plafond "
              f"({MAX_PAGES}), abandon", file=sys.stderr)
        return None

    for numero in range(2, last_page + 1):
        page = _lire_page(token, chemin, params, cle, numero)
        if page is None:
            return None  # jamais de liste incomplète sans le dire
        elements.extend(page[0])
    return elements

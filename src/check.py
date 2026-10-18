import sys

from requests import Response

from client import appeler, charger_token


def afficher(chemin: str, reponse: Response):
    try:
        contenu = reponse.json()
    except ValueError:
        print(f"code:{reponse.status_code}", "Non JSON", file=sys.stderr)
        return False
    code = reponse.status_code
    appels_restants = reponse.headers.get("X-RateLimit-Remaining")
    succes = contenu.get("success") if isinstance(contenu, dict) else None
    print(chemin, f"code:{code}", f"succès: {succes}",
          f"remaining: {appels_restants}")
    return code == 200 and succes is True


if __name__ == "__main__":
    liste_couples = [("/reference", None), ("/reviews", {"per_page": 1})]
    t = charger_token()
    for chemin, params in liste_couples:
        r = appeler(token=t, chemin=chemin, params=params)
        if r is None:
            print("erreur réseau", file=sys.stderr)
            sys.exit(1)
        if not afficher(chemin, r):
            sys.exit(1)
  




    

  


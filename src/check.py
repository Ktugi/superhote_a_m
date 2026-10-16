import os 
import sys
from pathlib import Path 

import keyring
from keyring.errors import KeyringError
from dotenv import load_dotenv
import requests
from requests import Response
from requests.exceptions import RequestException

SERVICE="Projet_avis5_sh"
UTILISATEUR="api_token"
BASE_URL="https://connect.superhote.com/api/v2/public"
TIMEOUT=30


def charger_token():
    token=None
    try:
        token=keyring.get_password(SERVICE,UTILISATEUR)
    except KeyringError:
        pass
    if not token:
        chemin_env=Path(__file__).resolve().parent.parent/".env"
        load_dotenv(chemin_env)
        token=os.getenv("SUPERHOTE_TOKEN")
    token=(token or "").strip()
    if not token:
        print("Aucun token trouvé. Verifie le coffre fort ou le fichier .env.",
              file=sys.stderr)
        sys.exit(1)
    return token

def appeler(token, chemin:str, params=None):
    URL=BASE_URL+chemin
    headers={"Authorization": f"Bearer {token}",
             "Accept":"application/json"}
    try:
      reponse=requests.get(url=URL,headers=headers,params=params,timeout=TIMEOUT)
    except RequestException as e:
      print("Appel echoué:",type(e).__name__,file=sys.stderr)
      reponse = None

    return reponse

def afficher(chemin:str ,reponse:Response):
    try:
        contenu=reponse.json()
    except ValueError:
        code=reponse.status_code
        print(f"code:{code}","Non JSON",file=sys.stderr)
        return False
    r_headers=reponse.headers
    code=reponse.status_code
    appels_restants=r_headers.get("X-RateLimit-Remaining")
    succes=contenu.get("success")
    print(chemin,f"code:{code}",f"succès: {succes}",
          f"remaining: {appels_restants}")
    if code == 200 and succes is True:
        return True
    else:
        return False

    



    





if __name__=="__main__":
    liste_couples=[("/reference",{}),("/reviews",{"per_page":"mouk"})]
    t=charger_token()
    for couple in liste_couples:
        r=appeler(token=t,chemin=couple[0],params=couple[1])
        if r is None:
            print("erreur reseau",file=sys.stderr)
            sys.exit(1)
        a=afficher(chemin=couple[0],reponse=r)
        if a is False:
            sys.exit(1)
    
    
        
  




    

  


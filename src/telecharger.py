from check import charger_token, appeler
import sys
import json
from pathlib import Path


token=charger_token()

liste_reservations=[]
for i in range(1,22):
    reponse=appeler(token,"/reservations",{"per_page":100,"page":i})
    if reponse is None:
        sys.exit(1)
    reservations=reponse.json().get("result").get("reservations")
    for reservation in reservations:
        liste_reservations.append(reservation)



fichier_json=Path(__file__).resolve().parent.parent/"data"/"reservations.json"
with open(fichier_json,"w",encoding="utf-8")as fichier:
    json.dump(liste_reservations,fichier,indent=2,ensure_ascii=False)








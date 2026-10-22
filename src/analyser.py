import json
from pathlib import Path



#AVIS

fichier_json=Path(__file__).resolve().parent.parent/"data"/"avis.json"
with open(fichier_json,"r",encoding="utf-8")as fichier:
    liste_avis=json.load(fichier)


liste_avis_r_code=[]
liste_avis_5=[]
compteur_review_none=0
for avis in liste_avis:
    if avis.get("rating")==5:
            liste_avis_5.append(avis)
    if avis.get("reviewed_at")is None:
         compteur_review_none=compteur_review_none+1        
for avis in liste_avis_5: 
    code = avis.get("reservation_confirmation_code")         
    if code is not None and code != "":      
        liste_avis_r_code.append(code)
            
print(len(liste_avis))
print(len(liste_avis_5))
print(len(liste_avis_r_code))
print(len(set(liste_avis_r_code)))
print(compteur_review_none)



#RESERVATIONS

fichier_json=Path(__file__).resolve().parent.parent/"data"/"reservations.json"
with open(fichier_json,"r",encoding="utf-8")as fichier:
    liste_reservations=json.load(fichier)
  #détails analyse dans notes.txt

liste_cles_reservations=list(liste_reservations[1].keys())
print(liste_cles_reservations)



#COMPARAISON COMPLETE
ids_reservation=[]
liste_non_trouver=[]
for avis in liste_avis_5:
    Flag=False
    for reservation in liste_reservations:  
        if avis.get("reservation_confirmation_code")==reservation.get("external_id") and avis.get("rental_id") == reservation.get("rental_id"):
            ids_reservation.append(reservation.get("id"))
            Flag=True
    if not Flag:
        liste_non_trouver.append(avis)   

print(len(ids_reservation))
print(len(liste_avis_5))
print(len(liste_non_trouver))

  #52 dates avis anterieurs date reservation la + ancienne : Hypothèse vérifié

              
              
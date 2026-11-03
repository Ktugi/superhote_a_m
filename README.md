# SMS de remerciement automatiques pour les avis 5 étoiles

Outil Python qui envoie un SMS de remerciement personnalisé aux voyageurs ayant laissé un avis 5 étoiles sur Airbnb, en s'appuyant sur l'API publique V2 du channel manager [SuperHote](https://docs.superhote.com/api-v2/).

Développé pour une conciergerie de location courte durée, puis installé sur son Mac sous la forme d'un lanceur à double-cliquer.

## Le besoin

La conciergerie souhaitait remercier par SMS chaque voyageur satisfait, le lendemain de son avis, sans recopier les avis et les numéros à la main.

Deux contraintes rendaient la tâche moins simple qu'il n'y paraît :

- **L'API ne donne pas le numéro de téléphone du voyageur** (le champ `guest_phone` vaut toujours `null`, par choix RGPD). L'envoi passe donc par l'API elle-même, qui utilise le numéro qu'elle connaît sans l'exposer.
- **Un avis et sa réservation n'ont pas d'identifiant commun.** Le lien se fait par le code de confirmation Airbnb : `reservation_confirmation_code` côté avis, `external_id` côté réservation. Cette hypothèse a été vérifiée sur les données réelles avant d'écrire la logique d'envoi.

## Fonctionnement

```
Avis SuperHote ──► filtre ──► réservation correspondante ──► SMS ──► mémoire locale
```

À chaque lancement, le script :

1. lit tous les avis (pagination complète) ;
2. garde ceux qui sont **éligibles** : note de 5, code de confirmation présent, postérieurs à une date de départ, pas encore traités, et datés **d'avant aujourd'hui** à l'heure de Paris (envoi le lendemain de l'avis) ;
3. retrouve la réservation de chaque avis par une requête ciblée (même logement, séjour terminé dans les 45 jours précédant l'avis) ;
4. insère le prénom du voyageur dans le message choisi par l'utilisateur ;
5. envoie le SMS et enregistre le résultat.

## Choix techniques

**Pas de doublon, même en cas de panne.** L'avis est noté « en cours » dans la mémoire locale *avant* l'envoi, puis son statut est mis à jour après. Un plantage ou une coupure réseau pendant l'envoi laisse l'avis marqué : il n'est jamais renvoyé automatiquement, et le cas est signalé pour vérification manuelle.

**Réessais différenciés.** Les lectures (`GET`) sont réessayées jusqu'à 3 fois en cas d'erreur réseau ou serveur (`5xx`), avec une attente croissante, et respectent l'en-tête `Retry-After` en cas de limite de débit (`429`). L'envoi (`POST`) n'est jamais réessayé : une requête expirée peut avoir abouti, et la rejouer risquerait un second SMS.

**Un `201` ne veut pas dire « remis ».** La documentation SuperHote précise qu'un `201` confirme l'enregistrement du message, pas sa remise. Le script vérifie que le canal retenu dans la réponse est bien `sms`, et distingue les statuts `envoye`, `non_remis`, `refuse` et `incertain`.

**Simulation par défaut.** Sans l'option `--envoyer`, le script affiche les messages exacts qui partiraient, sans rien envoyer ni modifier.

**Garde-fous.** Au plus 20 envois par lancement (le reste part aux lancements suivants), et arrêt immédiat sur une erreur d'authentification, de permission ou de quota.

**Suivi des cas à vérifier.** Tant que des envois restent `incertain` ou `non_remis` dans la mémoire locale, chaque lancement le rappelle, en distinguant les deux : un message peut-être parti d'un côté, un message enregistré mais non remis par SMS de l'autre.

**Secrets hors du code.** Le token API est rangé dans le trousseau du système (via `keyring`), avec un fichier `.env` exclu de git comme solution de repli en développement. Il n'est jamais affiché, même dans les messages d'erreur.

**Codes de sortie exploitables.** Le script se termine avec `0` en cas de succès et `1` dès qu'une intervention est nécessaire. Les erreurs sont écrites sur la sortie d'erreur (`stderr`), séparée de l'affichage normal.

**Installation sans prérequis sur macOS.** Un Mac récent n'a pas de Python utilisable. Le script d'installation télécharge [uv](https://github.com/astral-sh/uv), qui installe Python 3.12 et les dépendances dans le dossier de l'outil, sans droits administrateur. Désinstaller revient à supprimer le dossier.

## Structure

```
src/
├── client.py        Accès à l'API : token, GET avec réessais, pagination, envoi
├── envoyer.py       Logique métier : éligibilité, correspondance, envoi, mémoire
├── check.py         Test de connexion et des permissions du token
├── telecharger.py   Export local des avis et réservations (exploration)
├── analyser.py      Vérification des hypothèses sur les données exportées
└── test_envoi.py    Test d'envoi sur une réservation choisie
install.sh           Installation macOS (Python, token, lanceur sur le Bureau)
uninstall.sh         Désinstallation
message.exemple.txt  Modèle de message, avec {prenom}
```

## Utilisation

### Prérequis

Un token API SuperHote (Plateformes → API) avec les permissions :

- `public-api:reviews.read`
- `public-api:reservations.read`
- `public-api:messages.write`

### Installation (macOS)

```bash
cd ~/superhote_a_m
bash install.sh
```

Le script installe Python, demande le token, teste la connexion, crée `data/message.txt` et `data/etat.json`, puis place un lanceur `Envoyer les SMS.command` sur le Bureau.

### Personnaliser

- **Message** : `data/message.txt`, en texte brut. `{prenom}` est remplacé par le prénom du voyageur.
- **Date de départ** : valeur `"depart"` dans `data/etat.json`. Les avis antérieurs sont ignorés.

### Avant toute commande

Les commandes ci-dessous se lancent **toujours depuis le dossier du projet**, avec l'environnement activé. À chaque nouvelle fenêtre de Terminal :

```bash
cd ~/superhote_a_m
source .venv/bin/activate
```

Adapter le chemin du `cd` si le dossier a été placé ailleurs. Lancées depuis un autre dossier, les commandes ne trouvent pas `src/envoyer.py`.

### Prévisualiser avant d'envoyer

Lancé sans argument, le script fonctionne en simulation : il parcourt les avis comme pour un envoi réel et montre quelles réservations sont concernées et le texte exact que recevra chaque voyageur, sans rien envoyer ni modifier. À faire avant un envoi réel, ou après avoir changé le message ou la date de départ :

```bash
python src/envoyer.py
```

### Envoyer

Double-clic sur `Envoyer les SMS` sur le Bureau, ou :

```bash
python src/envoyer.py --envoyer               # envoi réel de tous les avis éligibles
python src/envoyer.py --envoyer --limite 3    # envoi réel, 3 avis au plus
```

`--limite N` traite au plus N avis, en commençant par les plus anciens. Pratique pour un premier envoi réel (`--limite 1`), ou pour avancer par petits lots après avoir reculé la date de départ.

Exemple de sortie en simulation (données fictives) :

```
MODE SIMULATION (rien n'est envoyé)
Modèle : Bonjour {prenom}, merci beaucoup pour votre avis et pour votre séjour !
Date de départ : 2026-10-22
[SIMULATION] avis 1042 -> réservation 98765, 63 caractères : Bonjour Marie, merci beaucoup pour votre avis et pour votre séjour !
avis lus : 120 | à traiter : 1 | simule : 1
```

## Données personnelles

Le dépôt ne contient ni token, ni donnée de voyageur. Le dossier `data/` (mémoire des envois, message, exports d'exploration) et le fichier `.env` sont exclus par `.gitignore`. Les exports d'exploration ne sont utilisés qu'en local et restent hors de l'outil livré.

## Technologies

Python 3.9+ · `requests` · `keyring` · `zoneinfo` · bash · uv · API REST SuperHote V2

## Licence

Aucune licence : le code est publié à titre de démonstration. Tous droits réservés.

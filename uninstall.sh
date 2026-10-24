#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/.venv/bin/python" -c "import keyring; keyring.delete_password('Projet_avis5_sh', 'api_token')" 2>/dev/null
rm -f "$HOME/Desktop/Envoyer les SMS.command"
echo "Token retiré du trousseau et lanceur supprimé."
echo "Il reste à supprimer le dossier $DIR,"
echo "puis à révoquer le token dans SuperHote (Plateformes > API)."
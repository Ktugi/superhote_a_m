#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# 1/4 Python et bibliothèques (6.1)
echo "1/4 Installation de Python et des bibliothèques..."
OUTILS="$DIR/.outils"
export UV_PYTHON_INSTALL_DIR="$OUTILS/python"
export UV_CACHE_DIR="$OUTILS/cache"
if [ ! -x "$OUTILS/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh \
    | env UV_INSTALL_DIR="$OUTILS" UV_NO_MODIFY_PATH=1 sh
fi
"$OUTILS/uv" venv --python 3.12 .venv
"$OUTILS/uv" pip install --python .venv/bin/python -r requirements.txt

# 2/4 Token dans le trousseau, puis test de connexion
echo "2/4 Collez le token SuperHote (rien ne s'affiche), puis Entrée :"
read -r -s TOKEN
echo
if [ -z "$TOKEN" ]; then
  echo "Aucun token saisi, installation arrêtée."
  exit 1
fi
SH_TOKEN="$TOKEN" .venv/bin/python -c "import keyring, os; keyring.set_password('Projet_avis5_sh', 'api_token', os.environ['SH_TOKEN'].strip())"
unset TOKEN
.venv/bin/python src/check.py

# 3/4 Message et date de départ (6.2 et 6.3)
echo "3/4 Préparation du dossier data..."
mkdir -p data
if [ ! -f data/message.txt ]; then
  cp message.exemple.txt data/message.txt
fi
if [ ! -f data/etat.json ]; then
  .venv/bin/python src/envoyer.py --init
fi

# 4/4 Lanceur sur le Bureau (6.4)
echo "4/4 Création du lanceur sur le Bureau..."
LANCEUR="$HOME/Desktop/Envoyer les SMS.command"
cat > "$LANCEUR" <<EOF
#!/bin/bash
cd "$DIR" || exit 1
.venv/bin/python src/envoyer.py --envoyer
echo
read -n 1 -s -r -p "Terminé. Appuyez sur une touche pour fermer."
EOF
chmod +x "$LANCEUR"

echo
echo "Installation terminée."
echo "Message : $DIR/data/message.txt"
echo "Date de départ : $DIR/data/etat.json"
echo "Pour envoyer : double-cliquez sur « Envoyer les SMS » sur le Bureau."
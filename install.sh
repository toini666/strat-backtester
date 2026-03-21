#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Nebular Apollo — Installation${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    echo -e "${BLUE}🔹 Installation de Homebrew (gestionnaire de paquets)...${NC}"
    echo -e "${YELLOW}   → Ton mot de passe Mac va être demandé, c'est normal.${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Ajouter brew au PATH (Apple Silicon vs Intel)
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f "/usr/local/bin/brew" ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo -e "${GREEN}✅ Homebrew déjà installé.${NC}"
fi

# --- Python 3 ---
if ! command -v python3 &>/dev/null; then
    echo -e "${BLUE}🔹 Installation de Python 3...${NC}"
    brew install python
else
    echo -e "${GREEN}✅ Python 3 déjà installé.${NC}"
fi

# --- Node.js ---
if ! command -v npm &>/dev/null; then
    echo -e "${BLUE}🔹 Installation de Node.js...${NC}"
    brew install node
else
    echo -e "${GREEN}✅ Node.js déjà installé.${NC}"
fi

# --- Virtual environment Python ---
echo -e "${BLUE}🔹 Création de l'environnement Python...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${BLUE}🔹 Installation des dépendances Python...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# --- Frontend ---
echo -e "${BLUE}🔹 Installation des dépendances frontend...${NC}"
cd frontend
npm install --silent
cd ..

# --- Fichier .env ---
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Fichier .env créé.${NC}"
else
    echo -e "${GREEN}✅ Fichier .env déjà présent.${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation terminée !${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Pour lancer l'application : ${BLUE}bash start.sh${NC}"
echo ""

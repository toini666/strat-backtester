#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Nebular Apollo — Mise à jour${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# --- Récupérer les dernières modifications ---
echo -e "${BLUE}🔹 Récupération des mises à jour...${NC}"
git pull

# --- Dé-tracker presets.json si encore suivi par git (one-shot) ---
git rm --cached data/presets.json 2>/dev/null && echo -e "${BLUE}🔹 presets.json dé-tracké (tes presets sont conservés)${NC}" || true

# --- Mettre à jour les dépendances Python si besoin ---
echo -e "${BLUE}🔹 Mise à jour des dépendances Python...${NC}"
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# --- Mettre à jour le frontend si besoin ---
echo -e "${BLUE}🔹 Mise à jour des dépendances frontend...${NC}"
cd frontend
npm install --silent
cd ..

echo ""
echo -e "${GREEN}✅ Mise à jour terminée !${NC}"
echo -e "Pour lancer l'application : ${BLUE}bash start.sh${NC}"
echo ""

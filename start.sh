#!/bin/bash

# Configuration
PORT=8888
NOTEBOOK_DIR="notebooks"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- 3. Start Application ---
echo -e "${GREEN}🚀 Starting Nebular Apollo Platform...${NC}"

# Kill any existing processes on ports 8001 and 3000 (optional safety)
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start Backend
echo -e "${BLUE}🔹 Starting Backend API...${NC}"
# Run from root so 'backend' is treated as package and 'src' is in path
venv/bin/uvicorn backend.main:app --reload --port 8001 &
BACKEND_PID=$!

# Start Frontend
echo -e "${BLUE}🔹 Starting Frontend Dashboard...${NC}"
cd frontend
npm run dev -- --port 3000 --host &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}✅ System Online!${NC}"
echo -e "   - Backend: http://localhost:8001"
echo -e "   - Frontend: http://localhost:3000"

# Open Browser
sleep 5
open http://localhost:3000

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM
wait
# Check if dependencies are installed
if ! pip show vectorbt > /dev/null 2>&1; then
    echo -e "${BLUE}⬇️ Installation des dépendances...${NC}"
    pip install -r requirements.txt
    pip install jupyter
fi

# Check .env existence
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📝 Création du fichier de configuration .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✨ Fichier .env créé ! Pense à ajouter ton token TopStepX dedans.${NC}"
fi

# Launch Jupyter
echo -e "${GREEN}✅ Système prêt ! Lancement de l'interface...${NC}"
echo -e "${BLUE}💡 Utilise le lien ci-dessous pour ouvrir l'interface dans ton navigateur:${NC}"
echo ""

jupyter notebook $NOTEBOOK_DIR --port $PORT --no-browser

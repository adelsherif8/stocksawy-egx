#!/bin/bash
set -e

echo "=============================="
echo "  EGX Stock Intelligence Bot"
echo "=============================="

# Check for OpenAI key
if [ ! -f backend/.env ]; then
  echo ""
  echo "ERROR: backend/.env not found!"
  echo "Run: cp backend/.env.example backend/.env"
  echo "Then add your OpenAI API key to backend/.env"
  exit 1
fi

if ! grep -q "sk-" backend/.env; then
  echo ""
  echo "ERROR: OpenAI API key not set in backend/.env"
  exit 1
fi

echo ""
echo "Starting backend (FastAPI)..."
cd backend
# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
venv/bin/pip install -r requirements.txt -q
venv/bin/uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

echo "Starting frontend (React)..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=============================="
echo "  App running!"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "=============================="
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait

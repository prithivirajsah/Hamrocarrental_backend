## Run backend
pkill -f "uvicorn main:app"
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload







git init
git add .
git commit -m "Initial commit"
git branch -M main
git push -u origin main
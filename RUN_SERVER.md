## Run backend
pkill -f "uvicorn main:app"
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

## Git push command
git init
git add .
git commit -m "testing review system and mantaining ui  "
git branch -M main
git push -u origin main
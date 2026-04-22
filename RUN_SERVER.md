## Run backend
pkill -f "uvicorn main:app"
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload


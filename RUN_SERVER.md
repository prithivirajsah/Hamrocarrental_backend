## Run backend

source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

## If you see "Address already in use"

pkill -f "uvicorn main:app"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
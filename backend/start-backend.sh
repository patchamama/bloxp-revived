# Activar venv primero
source venv/bin/activate
uvicorn main:app --reload
# O sin activar venv:
#venv/bin/uvicorn main:app --reload
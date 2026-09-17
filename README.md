## Запуск

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

docker run --name bs-postgres -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=battleship -p 5433:5432 -d postgres:16

alembic upgrade head

uvicorn main:app --reload
```

## Тесты

```bash
pytest
```
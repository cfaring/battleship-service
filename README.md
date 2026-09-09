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

## TO DO

1) заменить random.choice на супер-секретный-разработанный SMC-метод
2) написать таблицу для восстановления состава потопленного корабля
3) придумать больше тестов
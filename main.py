import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from dotenv import load_dotenv
from Neo4jManager import Neo4jDatabaseManager  # Подключаем ваш класс для работы с Neo4j

# Загружаем конфигурации из .env файла
load_dotenv()

# Чтение данных подключения к базе из переменных окружения
DATABASE_URI = "bolt://localhost:7687"
DATABASE_USER = os.getenv("NEO4J_USER")
DATABASE_PASS = os.getenv("NEO4J_PASS")
ACCESS_TOKEN = os.getenv("NEO4J_TOKEN")

# Проверка наличия всех необходимых переменных окружения
if not DATABASE_USER or not DATABASE_PASS or not ACCESS_TOKEN:
    raise EnvironmentError("Отсутствуют обязательные переменные окружения: NEO4J_USERNAME, NEO4J_PASSWORD, API_TOKEN")

# Инициализация схемы аутентификации через OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Функция для проверки действительности токена
def verify_token(token: str = Depends(oauth2_scheme)):
    if token != ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token {token}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# Создание контекста lifespan для инициализации и закрытия соединения с базой данных
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация базы данных с использованием вашего класса
    app.state.db_manager = Neo4jDatabaseManager(DATABASE_URI, DATABASE_USER, DATABASE_PASS)
    yield
    app.state.db_manager.close()


app = FastAPI(lifespan=lifespan)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Разрешаем доступ с фронтенда
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все HTTP-методы
    allow_headers=["*"],  # Разрешаем все заголовки
)


# Модели данных для работы с API

class NodeSchema(BaseModel):
    label: str
    properties: dict
    relationships: list


# Эндпоинты API

@app.get("/nodes")
async def retrieve_all_nodes():
    nodes = app.state.db_manager.fetch_all_nodes()
    return nodes


@app.get("/nodes_with_relations")
async def retrieve_all_nodes_with_relations():
    nodes = app.state.db_manager.fetch_all_nodes_with_associations()
    return nodes


@app.get("/nodes/{id}")
async def retrieve_node(id: int):
    node = app.state.db_manager.fetch_node_with_associations(id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@app.post("/nodes", dependencies=[Depends(verify_token)])
async def create_node(node: NodeSchema):
    app.state.db_manager.create_node_and_associations(node.label, node.properties, node.relationships)
    return {"message": "Node and relationships added successfully"}


@app.delete("/nodes/{id}", dependencies=[Depends(verify_token)])
async def remove_node(id: int):
    app.state.db_manager.remove_node(id)
    return {"message": "Node and relationships deleted successfully"}

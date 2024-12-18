import os
import pytest
from fastapi.testclient import TestClient
from main import app
from dotenv import load_dotenv
from Neo4jManager import Neo4jDatabaseManager

# Загружаем конфигурации из .env файла
load_dotenv()

DATABASE_URI = "bolt://localhost:7687"
DATABASE_USER = os.getenv("NEO4J_USER")
DATABASE_PASS = os.getenv("NEO4J_PASS")
ACCESS_TOKEN = os.getenv("NEO4J_TOKEN")


@pytest.fixture(scope="function")
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="function", autouse=True)
async def prepare_and_cleanup():
    app.state.db_manager = Neo4jDatabaseManager(DATABASE_URI, DATABASE_USER, DATABASE_PASS)
    app.state.db_manager.clear_all_data()
    yield
    app.state.db_manager.close_connection()

def test_create_node(test_client):
    new_entity = {
        "label": "User",
        "properties": {
            "id": 754345345,
            "name": "Житель лучшего города Земли",
            "screen_name": "tyumenets",
            "home_town": "Тюмень",
            "sex": "1"
        },
        "relationships": []
    }
    response = test_client.post("/nodes", json=new_entity, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
    assert response.status_code == 200
    assert response.json()['message'] == "Node and relationships added successfully"

def test_remove_node(test_client):
    response = test_client.delete("/nodes/13327918", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
    assert response.status_code == 200
    assert response.json()['message'] == "Node and relationships deleted successfully"


def test_retrieve_all_nodes(test_client):
    response = test_client.get("/nodes", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_retrieve_node_by_id(test_client):
    response = test_client.get("/nodes/371468999", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    entity = data[0]
    assert entity['node']['properties']['id'] == 371468999
    assert 'name' in entity['node']['properties']
    assert entity['node']['properties']['name'] == "Виталий Струнин"

import os
from neo4j import GraphDatabase, Transaction
from dotenv import load_dotenv

# Загрузка конфигураций из .env файла
load_dotenv()


class Neo4jDatabaseManager:
    def __init__(self, uri, user, pwd):
        self.driver = GraphDatabase.driver(uri, auth=(user, pwd))

        # Проверка соединения с базой данных
        with self.driver.session() as session:
            result = session.run("RETURN 1")
            if result.single() is None:
                raise Exception("Не удалось установить соединение с базой данных Neo4j")
            print("Успешное соединение с базой данных Neo4j")

    def close(self):
        self.driver.close()

    def get_all_nodes(self):
        query = "MATCH (n) RETURN n.id AS id, labels(n) AS label"
        with self.driver.session() as session:
            query_result = session.run(query)
            return [{"id": record["id"], "label": record["label"][0]} for record in query_result]

    def get_node_with_relations(self, node_id):
        query = """
        MATCH (n)-[r]-(m)
        WHERE n.id = $id
        RETURN n AS node, r AS relation, m AS target
        """
        with self.driver.session() as session:
            query_result = session.run(query, id=node_id)
            nodes_info = []
            for record in query_result:
                nodes_info.append({
                    "node": {
                        "id": record["node"].element_id,
                        "label": record["node"].labels,
                        "properties": dict(record["node"]),
                    },
                    "relation": {
                        "type": record["relation"].type,
                        "properties": dict(record["relation"]),
                    },
                    "target": {
                        "id": record["target"].element_id,
                        "label": record["target"].labels,
                        "properties": dict(record["target"]),
                    }
                })
            return nodes_info

    def get_all_nodes_with_relations(self):
        query = """
        MATCH (n)-[r]-(m)
        RETURN n AS node, r AS relation, m AS target
        """
        with self.driver.session() as session:
            query_result = session.run(query)

            node_relations = {}

            for record in query_result:
                node = record["node"]
                node_id = node.element_id
                if node_id not in node_relations:
                    node_relations[node_id] = {
                        "node": {
                            "id": node.element_id,
                            "label": node.labels,
                            "properties": dict(node),
                        },
                        "relations": []
                    }

                node_relations[node_id]["relations"].append({
                    "relation": {
                        "type": record["relation"].type,
                        "properties": dict(record["relation"]),
                    },
                    "target": {
                        "id": record["target"].element_id,
                        "label": record["target"].labels,
                        "properties": dict(record["target"]),
                    }
                })

            return list(node_relations.values())

    def add_node_with_relations(self, label, properties, relations):
        with self.driver.session() as session:
            session.execute_write(self._create_node_with_relations, label, properties, relations)

    @staticmethod
    def _create_node_with_relations(tx: Transaction, label, properties, relations):
        # Создание нового узла
        create_query = f"CREATE (n:{label} $properties) RETURN n"
        node = tx.run(create_query, properties=properties).single()["n"]
        node_id = node.element_id

        # Установка связей
        for relation in relations:
            tx.run(""" 
            MATCH (n), (m)
            WHERE n.id = $node_id AND m.id = $target_id
            CREATE (n)-[r:RELATION_TYPE]->(m)
            SET r = $relation_properties
            """, node_id=node_id, target_id=relation['target_id'],
                   relation_properties=relation['properties'])

    def delete_node(self, node_id):
        with self.driver.session() as session:
            session.execute_write(self._delete_node, node_id)

    @staticmethod
    def _delete_node(tx: Transaction, node_id):
        # Удаление узла и всех его связей
        tx.run("MATCH (n) WHERE n.id = $id DETACH DELETE n", id=node_id)


if __name__ == "__main__":
    # Параметры подключения из .env файла
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME")
    pwd = os.getenv("NEO4J_PASSWORD")

    # Проверка корректности загрузки переменных окружения
    if not user or not pwd:
        print("Ошибка: Отсутствуют параметры подключения к базе данных Neo4j в .env файле.")
        exit(1)

    print(f"Подключение к базе данных Neo4j с URI: {uri} и пользователем: {user}")

    # Инициализация менеджера базы данных
    db_manager = Neo4jDatabaseManager(uri, user, pwd)

    print("Получение всех узлов с их связями:")
    all_nodes = db_manager.get_all_nodes_with_relations()
    for node in all_nodes[:100]:
        print(node, end="\n\n")

    # Закрытие соединения с базой данных
    db_manager.close()

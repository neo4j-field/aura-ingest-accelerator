# tests/conftest.py
import os
import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


@pytest.fixture(scope="session")
def neo4j_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "testpassword")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    yield driver
    driver.close()


@pytest.fixture(autouse=True)
def clean_graph(neo4j_driver):
    """Wipe test labels before each test."""
    with neo4j_driver.session() as session:
        session.run("MATCH (n:TestNode) DETACH DELETE n")
        session.run("MATCH (n:TestRelNode) DETACH DELETE n")
    yield


@pytest.fixture
def sample_rows() -> list[dict]:
    return [
        {"id": i, "name": f"Name{i}", "status": "active" if i % 2 == 0 else "inactive"}
        for i in range(1, 26)
    ]

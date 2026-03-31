import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

@pytest.mark.asyncio
async def test_analyze_valid_ingredients():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": ["rice", "lentils", "spinach"]})
    assert response.status_code == 200
    data = response.json()
    assert "vitality_score" in data

@pytest.mark.asyncio
async def test_vitality_score_range():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": ["apple"]})
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["vitality_score"] <= 100

@pytest.mark.asyncio
async def test_all_response_fields_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": ["apple"]})
    assert response.status_code == 200
    data = response.json()
    fields = [
        "vitality_score", "deficiencies", "health_risks", "survival_recipes",
        "body_timeline", "meal_plan", "oracle_verdict", "aura_color"
    ]
    for field in fields:
        assert field in data

@pytest.mark.asyncio
async def test_empty_ingredients_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": []})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_too_many_ingredients_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": ["apple"] * 51})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_health_risks_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": ["apple"]})
    assert response.status_code == 200
    data = response.json()
    for risk in data["health_risks"]:
        assert "severity" in risk

@pytest.mark.asyncio
async def test_survival_recipes_count():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": ["apple"]})
    assert response.status_code == 200
    data = response.json()
    assert len(data["survival_recipes"]) == 3

@pytest.mark.asyncio
async def test_aura_color_is_hex():
    import re
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-ingredients", json={"ingredients": ["apple"]})
    assert response.status_code == 200
    data = response.json()
    assert re.match(r'^#[0-9a-fA-F]{6}$', data["aura_color"])

@pytest.mark.asyncio
async def test_image_endpoint_exists():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/analyze-image", json={})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_quick_tip_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/quick-tip")
    assert response.status_code == 200
    assert "tip" in response.json()

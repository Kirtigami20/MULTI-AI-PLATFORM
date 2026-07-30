import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from bson import ObjectId

from routes.tools import router
from utils.dependencies import get_current_user


# ---------------------------------------------------------------------------
# App + dependency overrides
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router)


def mock_user():
    return {"_id": ObjectId("000000000000000000000001"), "email": "test@test.com"}


app.dependency_overrides[get_current_user] = mock_user


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# POST /api/v1/tools
# ---------------------------------------------------------------------------

class TestCreateToolEndpoint:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_create_success(self, mock_get_col, client):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_col.insert_one.return_value = None
        mock_get_col.return_value = mock_col

        payload = {"name": "calculator", "description": "Calc", "tool_type": "builtin"}
        resp = await client.post("/api/v1/tools", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "calculator"
        assert data["tool_type"] == "builtin"

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_create_duplicate(self, mock_get_col, client):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {"_id": ObjectId(), "name": "calculator"}
        mock_get_col.return_value = mock_col

        resp = await client.post("/api/v1/tools", json={"name": "calculator", "tool_type": "builtin"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/v1/tools
# ---------------------------------------------------------------------------

class TestListToolsEndpoint:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_list_tools(self, mock_get_col, client):
        from unittest.mock import MagicMock
        mock_col = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_cursor.sort.return_value = mock_cursor
        mock_col.find.return_value = mock_cursor
        mock_get_col.return_value = mock_col

        resp = await client.get("/api/v1/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/tools/{tool_id}
# ---------------------------------------------------------------------------

class TestGetToolEndpoint:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_get_found(self, mock_get_col, client):
        tool_id = str(ObjectId())
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": ObjectId(tool_id),
            "user_id": "000000000000000000000001",
            "name": "calculator",
            "description": "Calc",
            "tool_type": "builtin",
            "config": {},
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_get_col.return_value = mock_col

        resp = await client.get(f"/api/v1/tools/{tool_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "calculator"

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_get_not_found(self, mock_get_col, client):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        resp = await client.get(f"/api/v1/tools/{ObjectId()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/tools/{tool_id}
# ---------------------------------------------------------------------------

class TestUpdateToolEndpoint:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_update_success(self, mock_get_col, client):
        tool_id = str(ObjectId())
        original = {
            "_id": ObjectId(tool_id),
            "user_id": "000000000000000000000001",
            "name": "calculator",
            "description": "Old",
            "tool_type": "builtin",
            "config": {},
            "created_at": "2026-01-01T00:00:00Z",
        }
        updated = dict(original, name="calc_v2")
        mock_col = AsyncMock()
        mock_col.find_one.side_effect = [original, updated]
        mock_col.update_one.return_value = None
        mock_get_col.return_value = mock_col

        resp = await client.put(f"/api/v1/tools/{tool_id}", json={"name": "calc_v2"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "calc_v2"

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_update_not_found(self, mock_get_col, client):
        valid_id = str(ObjectId())
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        resp = await client.put(f"/api/v1/tools/{valid_id}", json={"name": "new_name"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/tools/{tool_id}
# ---------------------------------------------------------------------------

class TestDeleteToolEndpoint:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_delete_success(self, mock_get_col, client):
        tool_id = str(ObjectId())
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {"_id": ObjectId(tool_id)}
        mock_col.delete_one.return_value = None
        mock_get_col.return_value = mock_col

        resp = await client.delete(f"/api/v1/tools/{tool_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_delete_not_found(self, mock_get_col, client):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        resp = await client.delete(f"/api/v1/tools/{ObjectId()}")
        assert resp.status_code == 404

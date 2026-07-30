import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from fastapi import HTTPException

from services.tool import ToolService
from schemas.tool import ToolCreate, ToolUpdate


def make_mock_doc(tool_id=None, name="calculator", tool_type="builtin", user_id="user1"):
    return {
        "_id": ObjectId(tool_id) if tool_id else ObjectId(),
        "user_id": user_id,
        "name": name,
        "description": "A tool",
        "tool_type": tool_type,
        "config": {},
        "created_at": "2026-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class TestToolServiceCreate:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_create_builtin_tool_success(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_col.insert_one.return_value = None
        mock_get_col.return_value = mock_col

        data = ToolCreate(name="calculator", description="Calc", tool_type="builtin")
        result = await ToolService.create(data, "user1")
        assert result["name"] == "calculator"
        assert result["tool_type"] == "builtin"
        mock_col.insert_one.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_create_duplicate_name_raises(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = make_mock_doc(name="calculator")
        mock_get_col.return_value = mock_col

        data = ToolCreate(name="calculator", tool_type="builtin")
        with pytest.raises(HTTPException) as exc_info:
            await ToolService.create(data, "user1")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_create_unknown_builtin_raises(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        data = ToolCreate(name="fake_tool", tool_type="builtin")
        with pytest.raises(HTTPException) as exc_info:
            await ToolService.create(data, "user1")
        assert exc_info.value.status_code == 400
        assert "Unknown built-in tool" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_create_api_tool_success(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_col.insert_one.return_value = None
        mock_get_col.return_value = mock_col

        data = ToolCreate(
            name="my_api",
            description="Custom API",
            tool_type="api",
            config={"url": "https://api.example.com", "method": "GET"},
        )
        result = await ToolService.create(data, "user1")
        assert result["name"] == "my_api"
        assert result["tool_type"] == "api"


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class TestToolServiceList:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_list_by_user(self, mock_get_col):
        from unittest.mock import MagicMock
        mock_col = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[make_mock_doc(), make_mock_doc()])
        mock_cursor.sort.return_value = mock_cursor
        mock_col.find.return_value = mock_cursor
        mock_get_col.return_value = mock_col

        result = await ToolService.list_by_user("user1")
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_list_empty(self, mock_get_col):
        from unittest.mock import MagicMock
        mock_col = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_cursor.sort.return_value = mock_cursor
        mock_col.find.return_value = mock_cursor
        mock_get_col.return_value = mock_col

        result = await ToolService.list_by_user("user1")
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------

class TestToolServiceGetById:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_get_found(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = make_mock_doc()
        mock_get_col.return_value = mock_col

        tool_id = str(ObjectId())
        result = await ToolService.get_by_id(tool_id, "user1")
        assert result["name"] == "calculator"

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_get_not_found(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        with pytest.raises(HTTPException) as exc_info:
            await ToolService.get_by_id(str(ObjectId()), "user1")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class TestToolServiceUpdate:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_update_success(self, mock_get_col):
        mock_col = AsyncMock()
        original = make_mock_doc()
        updated = make_mock_doc()
        updated["name"] = "calc_v2"
        mock_col.find_one.side_effect = [original, updated]
        mock_col.update_one.return_value = None
        mock_get_col.return_value = mock_col

        data = ToolUpdate(name="calc_v2")
        result = await ToolService.update(str(ObjectId()), data, "user1")
        assert result["name"] == "calc_v2"
        mock_col.update_one.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_update_not_found(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        with pytest.raises(HTTPException) as exc_info:
            await ToolService.update(str(ObjectId()), ToolUpdate(name="new_name"), "user1")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestToolServiceDelete:

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_delete_success(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = make_mock_doc()
        mock_col.delete_one.return_value = None
        mock_get_col.return_value = mock_col

        await ToolService.delete(str(ObjectId()), "user1")
        mock_col.delete_one.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.tool.get_collection")
    async def test_delete_not_found(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        with pytest.raises(HTTPException) as exc_info:
            await ToolService.delete(str(ObjectId()), "user1")
        assert exc_info.value.status_code == 404

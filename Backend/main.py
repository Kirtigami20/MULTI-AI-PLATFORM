from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import connect_db, close_db, get_collection
from routes.auth import router as auth_router
from routes.upload import router as upload_router
from routes.knowledge import router as knowledge_router
from routes.agent import router as agent_router
from routes.tools import router as tools_router
from routes.chat import router as chat_router
from routes.conversations import router as conversations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await _create_indexes()
    yield
    await close_db()


async def _create_indexes():
    try:
        conversations = get_collection("conversations")
        await conversations.create_index("user_id")
        await conversations.create_index("agent_id")
        await conversations.create_index("updated_at")
        messages = get_collection("messages")
        await messages.create_index("conversation_id")
        await messages.create_index("timestamp")
    except Exception as e:
        print(f"Index creation warning: {e}")


app = FastAPI(
    title="AI Agent Platform",
    description="No-code AI Agent Platform inspired by Lyzr",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(tools_router)
app.include_router(chat_router)
app.include_router(conversations_router)


@app.get("/")
async def root():
    return {
        "message": "AI Agent Platform API",
        "docs": "/docs",
        "version": "1.0.0",
    }

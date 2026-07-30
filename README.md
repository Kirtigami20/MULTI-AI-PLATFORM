# AI Agent Platform

An end-to-end AI Agent Platform that enables users to create, configure, and interact with intelligent AI agents. The platform supports custom tools, knowledge bases, RAG (Retrieval-Augmented Generation), conversation history, and multiple LLM providers through a modern web interface.

## Features

- 🤖 AI Agent Management
  - Create, update, and delete AI agents
  - Configure agent roles and instructions
  - Support for multiple LLMs

- 🛠️ Tool Builder
  - Create custom API tools
  - OpenAI-compatible function calling
  - Dynamic tool execution

- 📚 Knowledge Base
  - Upload and manage documents
  - Retrieval-Augmented Generation (RAG)
  - Semantic document retrieval

- 💬 Conversation Management
  - Persistent chat sessions
  - Conversation history stored in MongoDB
  - Resume previous conversations
  - Session-based chat interface

- 🧠 AI Capabilities
  - Tool Calling
  - Context-aware conversations
  - Multi-turn memory
  - Knowledge Base integration
  - General reasoning

- 🔒 Authentication
  - User authentication
  - Secure API access

---

## Tech Stack

### Backend

- FastAPI
- MongoDB
- Pydantic
- LangChain
- OpenAI Compatible APIs
- Ollama

### Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- Shadcn UI

---

## Project Structure

```
AI-Agent-Platform/
│
├── Backend/
│   ├── api/
│   ├── models/
│   ├── repositories/
│   ├── routers/
│   ├── services/
│   ├── runtime/
│   ├── engines/
│   ├── prompts/
│   ├── utils/
│   └── main.py
│
├── Frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── App.tsx
│
└── README.md
```

---

## Workflow

```
User
   │
   ▼
Select Agent
   │
   ▼
Chat Request
   │
   ▼
Tool Calling (if required)
   │
   ▼
Knowledge Base Retrieval (RAG)
   │
   ▼
LLM Response
   │
   ▼
Conversation Stored in MongoDB
```

---

## Current Features

- AI Agent Builder
- Tool Builder
- Knowledge Base Management
- Document Upload
- Tool Calling
- RAG Integration
- Conversation History
- Session Management
- MongoDB Storage
- FastAPI REST APIs
- React Dashboard

---

## Installation

### Backend

```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

---

## Future Enhancements

- Multi-Agent Collaboration
- Workflow Automation
- Voice Interaction
- Vector Database Support
- Agent Analytics
- Conversation Search
- Agent Marketplace

---

## Author

**Kirti Gami**

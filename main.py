import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import uuid
import uvicorn
import httpx
import json
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from pydantic import BaseModel
from aiintime_agent.config import get_config
from aiintime_agent.runner import agent_runner

master_agent_settings = get_config().master_agent
agent_settings = get_config().agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_runner.initialize_runner()
    print("Runner initialized")

    httpx.post(
        master_agent_settings.base_url + "/register_agent",
        json={
            "agent_name": agent_settings.name,
            "agent_card": json.load(open("agent-card.json")),
            "agent_base_url": agent_settings.base_url,
        }
    )
    yield

app = FastAPI(
    title="AIINTIME Agent API",
    description="AIINTIME Agent API",
    version="0.0.1",
    lifespan=lifespan
)

class ChatRequest(BaseModel):
    parent_session_id: str
    user_id: str
    message: str

@app.post("/delegate")
async def delegate(request: ChatRequest, background_tasks: BackgroundTasks):

    session_id = str(uuid.uuid4())
    await agent_runner.create_new_session(
        user_id=request.user_id,
        session_id=session_id
    )
    
    background_tasks.add_task(
        agent_runner.run_async_chat,
        request.parent_session_id,
        session_id,
        request.user_id,
        request.message
    )
    return {
        "message" : "Tell user that the request is being processed. Ask User to wait for the response."
    }


if __name__ == "__main__":
    app_config = get_config().app
    uvicorn.run(
        app, 
        host=app_config.host,
        port=app_config.port
    )

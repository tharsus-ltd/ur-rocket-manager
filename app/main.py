import asyncio
import json
import sys
import logging
from typing import List

from fastapi import Depends, FastAPI, status, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app import __root__, __service__, __version__, __startup_time__
from app.handlers import Handlers
from app.models import Rocket, RocketBase
from app.rockets import (calc_initial_fuel, generate_unique_id, get_rocket,
                         get_rockets_for_user, set_rocket)
from app.security import get_username_from_token

app = FastAPI(title=__service__, root_path=__root__, version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    # Wait for RabbitMQ and Redis
    await asyncio.sleep(__startup_time__)
    await Handlers().init()
    asyncio.create_task(Handlers().crash_check())
    asyncio.create_task(Handlers().launcher())


@app.get("/")
async def root():
    return {"Service": __service__, "Version": __version__}


@app.get("/status")
async def get_status():
    # Add checks to ensure the system is running
    return False


@app.post("/rockets", response_model=Rocket)
async def create_rocket(
    inp_rocket: RocketBase,
    username: str = Depends(get_username_from_token)
):
    # Create a rocket, start by checking parameters
    id = await generate_unique_id(50)
    rocket = Rocket(**inp_rocket.dict(), id=id, fuel=calc_initial_fuel(inp_rocket))
    await set_rocket(rocket, username)
    msg = {
        "rocket": rocket.dict(),
        "username": username
    }
    await Handlers().send_msg(json.dumps(msg), f"rocket.{id}.created")
    return rocket


@app.get("/rockets", response_model=List[Rocket])
async def get_user_rockets(
    *, username: str = Depends(get_username_from_token)
):
    return await get_rockets_for_user(username)


@app.put("/rockets/{id}", response_model=Rocket)
async def edit_rocket(
    id: str,
    new_rocket: RocketBase,
    username: str = Depends(get_username_from_token)
):
    rocket = await get_rocket(id, username)

    if rocket.launched or rocket.altitude > 0 or rocket.crashed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot change a rocket once it has been launched",
        )
    rocket.height = new_rocket.height
    rocket.num_engines = new_rocket.num_engines
    rocket.fuel = calc_initial_fuel(new_rocket)
    await set_rocket(rocket, username)
    return rocket


@app.delete("/rockets/{id}", response_model=Rocket)
async def delete_rocket(
    id: str,
    username: str = Depends(get_username_from_token)
):
    return await delete_rocket(id, username)


@app.put("/rockets/{id}/launch")
async def launch_rocket(
    id: str,
    username: str = Depends(get_username_from_token)
):
    # 1. Get rocket from database with id
    rocket = await get_rocket(id, username)
    rocket.launched = True
    await set_rocket(rocket, username)

    # 3. Send rocket launch event
    msg = {
        "rocket": rocket.dict(),
        "username": username
    }
    topic = f"rocket.{rocket.id}.launched"
    await Handlers().send_msg(json.dumps(msg), topic)
    return rocket


@app.websocket("/rocket/{id}/ws")
async def rocket_realtime(
    websocket: WebSocket,
    id: str
):
    # Accept the websocket
    await websocket.accept()

    try:
        # Create a queue to monitor the rocket update events:
        queue = await Handlers().channel.declare_queue(f"realtime-{id}")
        await queue.bind(Handlers().exchange, f"rocket.{id}.launched")
        await queue.bind(Handlers().exchange, f"rocket.{id}.updated")
        await queue.bind(Handlers().exchange, f"rocket.{id}.crashed")

        # if we get a rocket update event, send this out:
        async with queue.iterator() as q_iter:
            async for message in q_iter:
                async with message.process():
                    logger.info("rocket updated, sending msg to ws")
                    await websocket.send_text(message.body.decode())

    except WebSocketDisconnect:
        await queue.delete()

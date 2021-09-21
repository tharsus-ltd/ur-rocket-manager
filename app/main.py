import asyncio
import json
from typing import List
from uuid import uuid4

from fastapi import Depends, FastAPI

from app import __root__, __service__, __version__
from app.handlers import Handlers
from app.models import Rocket, RocketCreate
from app.rockets import (calc_initial_fuel, crash_rocket, get_rocket,
                         get_rockets_for_user, set_rocket, update_rocket)
from app.security import get_username_from_token

app = FastAPI(title=__service__, root_path=__root__, version=__version__)


@app.on_event("startup")
async def startup():
    # Wait for RabbitMQ and Redis
    await asyncio.sleep(20)
    await Handlers().init()
    asyncio.create_task(Handlers().crash_check(crash_rocket))
    asyncio.create_task(Handlers().launcher(update_rocket))


@app.get("/")
async def root():
    return {"Service": __service__, "Version": __version__}


@app.get("/status")
async def status():
    # Add checks to ensure the system is running
    return False


@app.post("/rockets", response_model=Rocket)
async def create_rocket(
    inp_rocket: RocketCreate,
    username: str = Depends(get_username_from_token)
):
    # Create a rocket, start by checking parameters
    id = str(uuid4())
    rocket = Rocket(**inp_rocket.dict(), id=id, fuel=calc_initial_fuel(inp_rocket))
    await set_rocket(rocket, username)
    msg = {
        "rocket": rocket.dict(),
        "username": username
    }
    await Handlers().send_msg(json.dumps(msg), "rocket.created")
    return rocket


@app.get("/rockets", response_model=List[Rocket])
async def get_user_rockets(
    *, username: str = Depends(get_username_from_token)
):
    return get_rockets_for_user(username)


@app.delete("/rockets/{id}")
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

    # 3. Send rocket launch event
    msg = {
        "rocket": rocket.dict(),
        "username": username
    }
    await Handlers().send_msg(json.dumps(msg), "rocket.launched")
    return rocket

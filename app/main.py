from uuid import uuid4
from fastapi import FastAPI

from app import __version__, __service__, __root__
from app.models import Rocket, RocketCreate
from app.rockets import calc_initial_fuel, get_rocket, set_rocket
from app.handlers import Handlers


app = FastAPI(title=__service__, root_path=__root__, version=__version__)


@app.on_event("startup")
async def startup():
    Handlers().init()


@app.get("/")
async def root():
    return {"Service": __service__, "Version": __version__}


@app.get("/status")
async def status():
    # Add checks to ensure the system is running
    return False


@app.post("/rockets", response_model=Rocket)
async def create_rocket(inp_rocket: RocketCreate):
    # Create a rocket, start by checking parameters
    id = str(uuid4())
    rocket = Rocket(**inp_rocket.dict(), id=id, fuel=calc_initial_fuel(inp_rocket))
    await set_rocket(rocket)
    await Handlers().send_msg(rocket.json(), "rocket.created")
    return rocket


@app.delete("/rockets/{id}")
async def delete_rocket(id: str):
    rocket = get_rocket(id)
    


@app.put("/rockets/{id}/launch")
async def launch_rocket(id: str):
    rocket = Rocket()
    # 1. Get rocket from database with id
    # 2. Update rocket state in db
    # 3. Send rocket launch event
    return rocket
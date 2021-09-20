import json

from app.handlers import Handlers
from math import pi
from app.models import Rocket, RocketCreate


def calc_initial_fuel(rocket: RocketCreate) -> float:
    dia = calc_rocket_diameter(rocket.num_engines)
    return rocket.height * pi * (0.5*dia)**2 


def calc_rocket_diameter(num_engines: int) -> float:
    if num_engines == 1:
        return 4
    return (num_engines / 2) * 4


def get_key(id: str) -> str:
    return f"r:{id}"


async def rocket_exists(id: str) -> bool:
    return (await Handlers().redis.exists(get_key(id))) == 1


async def set_rocket(rocket: Rocket):
    if await rocket_exists(rocket.id):
        raise KeyError(f"Rocket with id: {rocket.id} already exists in database")
    else:
        await Handlers().redis.set(get_key(rocket.id), rocket.json())
    

async def get_rocket(id: str) -> Rocket:
    if await rocket_exists(id):
        raw = await Handlers().redis.get(get_key(id))
        return Rocket(**json.loads(raw))
    else:
        raise KeyError(f"Rocket with id: {id} not found")


async def delete_rocket(id: str):
    pass
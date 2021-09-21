from app import RF_DENSITY, WALL_THICKNESS
import json
from typing import List

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


def calc_rocket_mass(rocket: Rocket) -> float:
    fuel = rocket.fuel * RF_DENSITY
    engine = 8400 * rocket.num_engines
    dia = calc_rocket_diameter(rocket.num_engines)
    body = pi * rocket.height * WALL_THICKNESS * (dia - WALL_THICKNESS)
    return fuel + engine + body


def get_key(id: str, username: str) -> str:
    return f"{username}:{id}"


async def rocket_exists(id: str, username: str) -> bool:
    return (await Handlers().redis.exists(get_key(id, username))) == 1


async def set_rocket(rocket: Rocket, username):
    if await rocket_exists(rocket.id, username):
        raise KeyError(f"Rocket with id: {rocket.id} already exists in database")
    else:
        await Handlers().redis.set(get_key(rocket.id, username), rocket.json())


async def get_rockets_for_user(username: str) -> List[Rocket]:
    rockets: List[Rocket] = []
    for key in Handlers().redis.hscan(match=f"{username}:*"):
        raw = json.loads(Handlers().redis.get(key))
        rockets.append(Rocket(**raw))

    return rockets


async def get_rocket(id: str, username: str) -> Rocket:
    if await rocket_exists(id, username):
        raw = await Handlers().redis.get(get_key(id, username))
        return Rocket(**json.loads(raw))
    else:
        raise KeyError(f"Rocket with id: {id} not found")


async def delete_rocket(id: str, username: str):
    rocket = get_rocket(id, username)
    await Handlers().redis.delete(get_key(id, username))
    return rocket

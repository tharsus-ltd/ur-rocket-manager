import asyncio
import json

from typing import List
from math import pi

from app import MASS_FLOW, RF_DENSITY, TIME_DELTA, WALL_THICKNESS
from app.handlers import Handlers
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
    body = pi * rocket.height * WALL_THICKNESS * (dia - WALL_THICKNESS) * 2700
    return fuel + engine + body


def calc_exhaust_vel(rocket: Rocket) -> float:
    if rocket.altitude < 170e3:
        return (rocket.altitude * 9.118e-6 + 2.58) * 1000
    else:
        return 4.13e3


def calc_acceleration(rocket: Rocket) -> float:
    if rocket.fuel <= 0:
        return -9.81
    m_dot = MASS_FLOW * rocket.num_engines
    v_exh = calc_exhaust_vel(rocket)
    a = ((v_exh * m_dot) / calc_rocket_mass(rocket)) - 9.81
    return a if a > 0 else 0


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


async def update_rocket(rocket: Rocket, username: str) -> Rocket:

    if rocket.crashed:
        return rocket

    # Pause for dt seconds to allow the rocket to "move"
    asyncio.sleep(TIME_DELTA)

    # Linear acceleration
    acc = calc_acceleration(rocket)
    d_pos = 0.5 * acc * TIME_DELTA**2 + rocket.velocity * TIME_DELTA

    # Update rocket values
    rocket.altitude += d_pos
    rocket.fuel -= MASS_FLOW * rocket.num_engines * TIME_DELTA
    rocket.velocity += acc * TIME_DELTA

    # Update max altitude
    if rocket.altitude > rocket.max_altitude:
        rocket.max_altitude = rocket.altitude

    # Save in database
    await Handlers().redis.set(get_key(rocket.id, username), rocket.json())
    msg = {
        "rocket": rocket.dict(),
        "username": username
    }
    await Handlers().send_msg(json.dumps(msg), "rocket.updated")
    return rocket


async def crash_rocket(rocket: Rocket, username: str) -> Rocket:
    rocket.crashed = True

    await Handlers().redis.set(get_key(rocket.id, username), rocket.json())
    msg = {
        "rocket": rocket.dict(),
        "username": username
    }
    await Handlers().send_msg(json.dumps(msg), "rocket.updated")
    return rocket

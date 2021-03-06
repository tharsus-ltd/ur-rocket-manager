import asyncio
import json
import logging
import opentracing

from typing import List
from math import pi

from app import MASS_FLOW, RF_DENSITY, TIME_DELTA, WALL_THICKNESS
from app.security import get_random_word
from app.handlers import Handlers
from app.models import Rocket, RocketBase


logger = logging.getLogger(__name__)


def calc_initial_fuel(rocket: RocketBase) -> float:
    dia = calc_rocket_diameter(rocket.num_engines)
    return (rocket.height * pi * (0.5*dia)**2)*0.25


def calc_rocket_diameter(num_engines: int) -> float:
    if num_engines == 1:
        return 2.5
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


async def generate_unique_id(retries: int = 10) -> str:
    with opentracing.tracer.start_active_span("generate_unique_id") as scope:
        for _ in range(retries):
            new_id = get_random_word()
            if not (await rocket_id_exists(new_id)):
                scope.span.set_tag("rocket_id", new_id)
                return new_id
        err = "Couldnt get unique id for rocket"
        scope.span.log_kv({"error": err})
        raise RuntimeError("Couldnt get unique id for rocket")


def calc_acceleration(rocket: Rocket) -> float:
    if rocket.fuel <= 0:
        return -9.81
    m_dot = MASS_FLOW * rocket.num_engines
    v_exh = calc_exhaust_vel(rocket)
    a = ((v_exh * m_dot) / calc_rocket_mass(rocket)) - 9.81
    return a if a > 0 else 0


def calc_rocket_fuel(rocket: Rocket) -> float:
    return (MASS_FLOW * rocket.num_engines * TIME_DELTA) / RF_DENSITY


def get_key(id: str, username: str) -> str:
    return f"{username}:{id}"


async def rocket_exists(id: str, username: str) -> bool:
    with opentracing.tracer.start_active_span("rocket_exists") as scope:
        res = (await Handlers().redis.exists(get_key(id, username))) >= 1
        scope.span.log_kv({"result": res})
        return res


async def rocket_id_exists(id: str) -> bool:
    with opentracing.tracer.start_active_span("rocket_id_exists") as scope:
        res = (await Handlers().redis.exists(f"*:{id}")) >= 1
        scope.span.log_kv({"result": res})
        return res


async def set_rocket(rocket: Rocket, username):
    with opentracing.tracer.start_active_span("set_rocket") as scope:
        scope.span.log_kv(rocket.dict())
        await Handlers().redis.set(get_key(rocket.id, username), rocket.json())


async def get_rockets_for_user(username: str) -> List[Rocket]:
    with opentracing.tracer.start_active_span("get_rockets_for_user") as scope:
        rockets: List[Rocket] = []
        scope.span.set_tag("user", username)
        async for key in Handlers().redis.scan_iter(f"{username}:*"):
            raw = await Handlers().redis.get(key)
            rockets.append(Rocket(**json.loads(raw)))
        scope.span.set_tag("rockets", len(rockets))
        return rockets


async def get_rocket(id: str, username: str) -> Rocket:
    with opentracing.tracer.start_active_span("get_rocket") as scope:
        if await rocket_exists(id, username):
            raw = await Handlers().redis.get(get_key(id, username))
            rocket = Rocket(**json.loads(raw))
            scope.span.log_kv(rocket.dict())
            return rocket
        else:
            err = f"Rocket with id: {id} not found"
            scope.span.log_kv({"error": err})
            raise KeyError(err)


async def delete_rocket(id: str, username: str):
    with opentracing.tracer.start_active_span("delete_rocket") as scope:
        rocket = await get_rocket(id, username)
        await Handlers().redis.delete(get_key(id, username))
        scope.span.log_kv(rocket.dict())
        return rocket


async def update_rocket(rocket: Rocket, username: str) -> Rocket:
    if rocket.crashed:
        return rocket

    # Pause for dt seconds to allow the rocket to "move"
    await asyncio.sleep(TIME_DELTA)

    # Grab the rocket from the db to check if it crashed while we waited
    latest_rocket = await get_rocket(rocket.id, username)
    if latest_rocket.crashed:
        # Make sure the frontend gets updated:
        msg = {
            "rocket": latest_rocket.dict(),
            "username": username
        }
        await Handlers().send_msg(json.dumps(msg), f"rocket.{rocket.id}.updated")
        return latest_rocket

    # Linear acceleration
    acc = calc_acceleration(rocket)
    d_pos = 0.5 * acc * TIME_DELTA**2 + rocket.velocity * TIME_DELTA

    # Update rocket values
    rocket.altitude += d_pos
    rocket.velocity += acc * TIME_DELTA

    if rocket.fuel > 0:
        d_fuel = calc_rocket_fuel(rocket)
        rocket.fuel -= d_fuel
        if rocket.fuel < 0:
            rocket.fuel = 0
            rocket.status = "Out of fuel ???????"
            await Handlers().send_msg(json.dumps({
                "rocket": rocket.dict(),
                "username": username
            }), f"rocket.{rocket.id}.nofuel")

    # Update max altitude
    if rocket.altitude > rocket.max_altitude:
        rocket.max_altitude = rocket.altitude

    # Save in database
    if rocket.fuel <= 0 and rocket.altitude <= 0:
        rocket = await crash_rocket(rocket, username, "Crash landed ????????")
        rocket.altitude = 0

    with opentracing.tracer.start_active_span("update_rocket") as scope:
        scope.span.log_kv(rocket.dict())
        await Handlers().redis.set(get_key(rocket.id, username), rocket.json())
        msg = {
            "rocket": rocket.dict(),
            "username": username
        }

    await Handlers().send_msg(json.dumps(msg), f"rocket.{rocket.id}.updated")
    return rocket


async def crash_rocket(rocket: Rocket, username: str, status: str) -> Rocket:
    with opentracing.tracer.start_active_span("crash_rocket") as scope:

        rocket.crashed = True
        rocket.status = status

        scope.span.log_kv(rocket.dict())

        await Handlers().redis.set(get_key(rocket.id, username), rocket.json())
        msg = {
            "rocket": rocket.dict(),
            "username": username
        }
        await Handlers().send_msg(json.dumps(msg), f"rocket.{rocket.id}.updated")
        return rocket

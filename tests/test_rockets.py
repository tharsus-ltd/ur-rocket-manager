import pytest

from hypothesis import given
from hypothesis import strategies as st

from app import MAX_ENGINES, MAX_HEIGHT, MIN_ENGINES, MIN_HEIGHT
from app.models import RocketBase
from app.handlers import Handlers
from app.rockets import (calc_initial_fuel, calc_rocket_diameter,
                         calc_rocket_mass, crash_rocket, generate_unique_id, get_key, get_rocket,
                         set_rocket)


@given(st.integers(MIN_ENGINES, MAX_ENGINES))
def test_diameter(e):
    assert calc_rocket_diameter(1) == 4
    assert calc_rocket_diameter(2) == 4
    assert calc_rocket_diameter(3) == 6
    assert calc_rocket_diameter(4) == 8
    assert calc_rocket_diameter(e) > 0


@given(st.integers(MIN_HEIGHT, MAX_HEIGHT), st.integers(MIN_ENGINES, MAX_ENGINES))
def test_fuel_calc(h, e):
    inp = RocketBase(height=h, num_engines=e)
    assert calc_initial_fuel(inp) > 0


def test_mass_calc(rocket):
    assert calc_rocket_mass(rocket) > 0


@pytest.mark.asyncio
async def test_crash_rocket(rocket, handlers, mocker):
    with mocker.patch.object(Handlers, "send_msg"):
        await crash_rocket(rocket, "test")
        assert rocket.crashed


@pytest.mark.asyncio
async def test_set_get_rocket(rocket, handlers):
    username = "test"
    assert (await handlers.redis.exists(get_key(rocket.id, username))) == 0
    await set_rocket(rocket, username)
    assert (await handlers.redis.exists(get_key(rocket.id, username))) == 1
    assert rocket == await get_rocket(rocket.id, username)


@pytest.mark.asyncio
async def test_create_id(handlers):
    id1 = await generate_unique_id()
    id2 = await generate_unique_id()
    assert id1 != id2

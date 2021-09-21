import pytest

from app.handlers import Handlers
from app.rockets import get_rocket, set_rocket, update_rocket
from app.models import RocketCreate
from app.main import create_rocket, launch_rocket


@pytest.mark.asyncio
async def test_rocket_creation(handlers, mocker):

    with mocker.patch.object(Handlers, "send_msg"):

        rocket = await create_rocket(
            RocketCreate(
                num_engines=4,
                height=200
            ),
            "test"
        )

        assert rocket.height == 200
        assert rocket.num_engines == 4
        assert rocket.fuel > 0

        assert await get_rocket(rocket.id, "test") == rocket

        Handlers.send_msg.assert_called_once()


@pytest.mark.asyncio
async def test_rocket_launch(handlers, rocket, mocker):

    with mocker.patch.object(Handlers, "send_msg"):

        await set_rocket(rocket, "test")
        await launch_rocket(rocket.id, "test")

        Handlers.send_msg.assert_called_once()

        # Fake calling update rocket:
        await update_rocket(rocket, "test")

        new_rocket = await get_rocket(rocket.id, "test")
        assert new_rocket.altitude > 0

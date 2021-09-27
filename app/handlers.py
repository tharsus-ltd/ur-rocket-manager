from app.models import Rocket
import json
import os
import asyncio
import logging
import aioredis

from aio_pika import Message, connect_robust, ExchangeType

from app.singleton import Singleton

REDIS_SERVICE = os.environ.get("REDIS_SERVICE", "rocket_man_db")

logger = logging.getLogger(__name__)


class Handlers(metaclass=Singleton):

    async def init(self):
        self.redis = aioredis.from_url(f"redis://{REDIS_SERVICE}", encoding="utf-8", decode_responses=True)
        self.rabbitmq = await connect_robust("amqp://guest:guest@rabbitmq/", loop=asyncio.get_event_loop())
        self.channel = await self.rabbitmq.channel()
        self.exchange = await self.channel.declare_exchange("micro-rockets", ExchangeType.TOPIC, durable=True)

    async def send_msg(self, msg: str, topic: str):
        await self.exchange.publish(
            Message(body=msg.encode()),
            routing_key=topic,
        )

    async def launcher(self):
        from app.rockets import update_rocket

        assert self.exchange is not None, "Error with exchange"

        queue = await self.channel.declare_queue("rocket-update")
        await queue.bind(self.exchange, "rocket.*.launched")
        await queue.bind(self.exchange, "rocket.*.updated")

        logging.info(f"Created bindings for {queue.name}")

        async with queue.iterator() as q_iter:
            async for message in q_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        rocket = Rocket(**data["rocket"])
                        username = data["username"]

                        await update_rocket(rocket, username)
                    except Exception as e:
                        logging.error(e)

        raise RuntimeError("Launcher loop exited")

    async def crash_check(self):
        from app.rockets import crash_rocket

        queue = await self.channel.declare_queue("crash-check")
        await queue.bind(self.exchange, "rocket.*.crashed")

        async with queue.iterator() as q_iter:
            async for message in q_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    rocket = Rocket(**data["rocket"])
                    username = data["username"]

                    status = data["status"] if "status" in data else rocket.status

                    if not rocket.crashed:
                        await crash_rocket(rocket, username, status)

import json
import os
import aioredis

from typing import Any
from aio_pika import Message, connect_robust

from app.singleton import Singleton

REDIS_SERVICE = os.environ.get("REDIS_SERVICE", "rocket_man_db")


class Handlers(metaclass=Singleton):

    async def init(self):
        self.redis = aioredis.from_url(f"redis://{REDIS_SERVICE}", encoding="utf-8", decode_responses=True)
        self.rabbitmq = await connect_robust("amqp://guest:guest@rabbitmq/")
        self.channel = await self.rabbitmq.channel()

    async def send_msg(self, msg: str, topic: str):
        await self.channel.default_exchange.publish(
            Message(body=msg.encode()),
            routing_key=topic,
        )

    async def launcher(self, callback: Any):
        queue = await self.channel.declare_queue("rocket-launch")
        queue.bind(self.channel.default_exchange, "rocket.launched")
        queue.bind(self.channel.default_exchange, "rocket.updated")

        async with queue.iterator() as q_iter:
            async for message in q_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    rocket = data["rocket"]
                    username = data["username"]

                    await callback(rocket, username)

    async def crash_check(self, callback: Any):
        queue = await self.channel.declare_queue("crash-check")
        queue.bind(self.channel.default_exchange, "rocket.crashed")

        async with queue.iterator() as q_iter:
            async for message in q_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    rocket = data["rocket"]
                    username = data["username"]

                    await callback(rocket, username)

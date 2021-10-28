import json
import os
import asyncio
import logging
from aio_pika.message import IncomingMessage
import aioredis
import opentracing

from contextlib import contextmanager
from opentracing.ext import tags
from typing import Any, Dict
from aio_pika import Message, connect_robust, ExchangeType
from opentracing.propagation import Format, InvalidCarrierException, SpanContextCorruptedException
from opentracing.tracer import follows_from

from app.singleton import Singleton
from app.models import Rocket

REDIS_SERVICE = os.environ.get("REDIS_SERVICE", "rocket_man_db")

logger = logging.getLogger(__name__)


@contextmanager
def message_tracer(message: IncomingMessage):
    span_ctx = None

    try:
        span_ctx = opentracing.tracer.extract(opentracing.Format.TEXT_MAP, message.headers)
    except (InvalidCarrierException, SpanContextCorruptedException):
        pass

    with opentracing.tracer.start_active_span(
        message.routing_key,
        references=follows_from(span_ctx),
        finish_on_close=True
    ) as scope:
        span = scope.span
        span.set_tag(tags.COMPONENT, "amqp")
        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_CONSUMER)
        yield scope


class Handlers(metaclass=Singleton):

    async def init(self):
        self.redis = aioredis.from_url(f"redis://{REDIS_SERVICE}", encoding="utf-8", decode_responses=True)
        self.rabbitmq = await connect_robust("amqp://guest:guest@rabbitmq/", loop=asyncio.get_event_loop())
        self.channel = await self.rabbitmq.channel()
        self.exchange = await self.channel.declare_exchange("micro-rockets", ExchangeType.TOPIC, durable=True)

    async def send_msg(self, msg: str, topic: str, propagate_trace: bool = True):
        with opentracing.tracer.start_active_span(topic) as scope:
            headers: Dict[str, Any] = {}
            if propagate_trace:
                opentracing.tracer.inject(scope.span, Format.TEXT_MAP, headers)
            scope.span.set_tag(tags.MESSAGE_BUS_DESTINATION, topic)
            scope.span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_PRODUCER)
            scope.span.set_tag(tags.COMPONENT, "amqp")
            await self.exchange.publish(
                Message(body=msg.encode(), headers=headers),
                routing_key=topic,
            )

    async def launcher(self):
        from app.rockets import update_rocket

        assert self.exchange is not None, "Error with exchange"

        queue = await self.channel.declare_queue("rocket-update")
        await queue.bind(self.exchange, "rocket.*.launched")
        await queue.bind(self.exchange, "rocket.*.updated")

        async with queue.iterator() as q_iter:
            async for message in q_iter:
                async with message.process():
                    try:
                        with message_tracer(message):
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
                    with message_tracer(message):
                        data = json.loads(message.body.decode())
                        rocket = Rocket(**data["rocket"])
                        username = data["username"]

                        status = data["status"] if "status" in data else rocket.status

                        if not rocket.crashed:
                            await crash_rocket(rocket, username, status)

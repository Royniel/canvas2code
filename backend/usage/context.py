import contextvars
from contextlib import asynccontextmanager

current_thread_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "thread_id", default=""
)
current_node_type: contextvars.ContextVar[str] = contextvars.ContextVar(
    "node_type", default="generate"
)


@asynccontextmanager
async def thread_context(thread_id: str):
    token = current_thread_id.set(thread_id)
    try:
        yield
    finally:
        current_thread_id.reset(token)


@asynccontextmanager
async def node_context(node_type: str):
    token = current_node_type.set(node_type)
    try:
        yield
    finally:
        current_node_type.reset(token)

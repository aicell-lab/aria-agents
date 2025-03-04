import os
from hypha_rpc import connect_to_server, login
from aiohttp import web
import asyncio
import json
from contextvars import copy_context, ContextVar
from schema_agents.utils.common import current_session, EventEmitter, EventBus

class AriaEventBus(EventBus):
    """Event bus that supports frontend-backend communication for corpus events"""
    def __init__(self):
        super().__init__()
        self.corpus_callbacks = {}

    def register_corpus_callback(self, session_id, callback):
        """Register a callback for corpus events"""
        self.corpus_callbacks[session_id] = callback

    def unregister_corpus_callback(self, session_id):
        """Unregister a corpus callback"""
        self.corpus_callbacks.pop(session_id, None)

    async def emit(self, event_type: str, args=None):
        """Emit an event, handling corpus events specially"""
        if event_type in ['list_corpus', 'get_corpus']:
            session_id = current_session.get().id
            callback = self.corpus_callbacks.get(session_id)
            if callback:
                return await callback({
                    "_corpus_event": event_type,
                    "_corpus_args": args
                })
            return None
        return await super().emit(event_type, args)

async def get_server(server_url, workspace_name=None, provided_token=None):
    login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    if login_required:
        token = (
            await login({"server_url": server_url})
            if provided_token is None
            else provided_token
        )
    else:
        token = None
    server = await connect_to_server(
        {
            "server_url": server_url,
            "token": token,
            "method_timeout": 500,
            **({"workspace": workspace_name} if workspace_name is not None else {}),
        }
    )
    return server

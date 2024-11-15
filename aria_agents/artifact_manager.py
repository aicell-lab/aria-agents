import httpx
import os
import aiofiles

class ArtifactManager:
    def __init__(self, event_bus=None):
        self.storage = {}
        self._svc = None
        self._prefix = None
        self.user_id = None
        self.session_id = None
        self._event_bus = event_bus

    async def setup(self, server, user_id, session_id, service_id="public/artifact-manager"):
        self._svc = await server.get_service(service_id)
        self.user_id = user_id
        self.session_id = session_id
        self._prefix = f"/ws-user-{user_id}/aria-agents-chats/{session_id}"

    async def put(self, value, name):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self._prefix, "Please set prefix using `set_prefix()` before using artifact manager"
        
        try:
            put_url = await self._svc.put_file(
                prefix=self._prefix,
                file_path=name
            )
            async with httpx.AsyncClient() as client:
                response = await client.put(put_url, data=value, timeout=500)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"File upload failed: {e}")
            raise RuntimeError(f"File upload failed: {e}") from e
        
        self._svc.commit(self._prefix)
        
        self._event_bus.emit("store_put", name)
        return name

    # TODO: fix URL so that it can be used to download the file as JSON
    async def get_url(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self._prefix, "Please set prefix using `set_prefix()` before using artifact manager"
        get_url = await self._svc.get_file(
            prefix=self._prefix,
            path=name
        )
        return get_url

    async def get(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self._prefix, "Please set prefix using `set_prefix()` before using artifact manager"
        get_url = await self.get_url(name)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(get_url, timeout=500)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise RuntimeError(f"File download failed: {e}") from e
        
        return response.text
    
    def get_event_bus(self):
        return self._event_bus

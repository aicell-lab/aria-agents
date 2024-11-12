import httpx
import os
import aiofiles

class ArtifactManager:
    def __init__(self, event_bus=None):
        self.storage = {}
        self._svc = None
        self._prefix = None
        self.session_id = None
        self._event_bus = event_bus

    async def setup(self, server, prefix, service_id="public/artifact-manager"):
        self._svc = await server.get_service(service_id)
        self._prefix = prefix

    def set_session_id(self, session_id):
        self.session_id = session_id

    async def put(self, value, name):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        print(f"Uploading {name} to {self._prefix}/{self.session_id}")
        put_url = await self._svc.put_file(
            prefix=f"{self._prefix}/{self.session_id}",
            file_path=name
        )
        print(f"Uploading {name} to {put_url}")
        
        try:
            response = await httpx.put(put_url, data=value, timeout=500)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise RuntimeError(f"File upload failed: {e}") from e
        
        self._svc.commit(f"{self._prefix}/{self.session_id}")
        
        self._event_bus.emit("store_put", self.session_id, name)
        return name

    async def get_url(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        get_url = await self._svc.get_file(
            prefix=f"{self._prefix}/{self.session_id}",
            path=name
        )
        return get_url

    async def get(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        get_url = await self.get_url(name)
        
        try:
            response = await httpx.get(get_url, timeout=500)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise RuntimeError(f"File download failed: {e}") from e
        
        return response.text
    
    def get_event_bus(self):
        return self._event_bus

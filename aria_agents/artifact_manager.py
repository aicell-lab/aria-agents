import requests

class ArtifactManager:
    def __init__(self, event_bus=None):
        self.storage = {}
        self._svc = None
        self._prefix = None
        self._event_bus = event_bus

    async def setup(self, server, prefix, service_id="public/artifact-manager"):
        self._svc = await server.get_service(service_id)
        self._prefix = prefix
        
    async def put(self, session_id, value, name):
        assert self._svc, "Please call `setup()` before using artifact manager"
        put_url = await self._svc.put_file(
            prefix=f"{self._prefix}/{session_id}",
            file_path=name
        )

        response = requests.put(put_url, data=value, timeout=500)

        assert response.ok, "File upload failed"
        
        self._svc.commit(f"{self._prefix}/{session_id}")
        
        self._event_bus.emit("store_put", session_id, name)
        return name
        

    async def get_url(self, session_id, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        get_url = await self._svc.get_file(
            prefix=f"{self._prefix}/{session_id}",
            path=name
        )
        return get_url

    async def get(self, session_id, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        get_url = self.get_url(session_id, name)
        
        response = requests.get(get_url, timeout=500)
        
        assert response.ok, "File download failed"
        return response.text
    
    def get_event_bus(self):
        return self._event_bus

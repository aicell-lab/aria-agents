import requests
import os

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
        
    async def put_dir(self, session_id, local_path, file_prefix=None):
        for filename in os.listdir(local_path):
            file_path = os.path.join(local_path, filename)
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
                await self.put(
                    session_id=session_id,
                    value=file_content,
                    name=filename
                )
                
    async def list_dir(self, session_id, file_prefix):
        all_files = await self._svc.list_files(f"{self._prefix}/{session_id}")
        
        def file_has_prefix(this_file):
            return this_file.name.startswith(file_prefix)
        
        return list(filter(file_has_prefix, all_files))

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

import requests
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
        put_url = await self._svc.put_file(
            prefix=f"{self._prefix}/{self.session_id}",
            file_path=name
        )
        
        try:
            response = await requests.put(put_url, data=value, timeout=500)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"File upload failed: {e}") from e
        
        self._svc.commit(f"{self._prefix}/{self.session_id}")
        
        self._event_bus.emit("store_put", self.session_id, name)
        return name
        
    async def put_dir(self, local_path, file_prefix=None):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        for filename in os.listdir(local_path):
            file_path = os.path.join(local_path, filename)
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
                await self.put(
                    value=file_content,
                    name=filename
                )
                
    async def list_dir(self, file_prefix):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        all_files = await self._svc.list_files(f"{self._prefix}/{self.session_id}")
        
        def file_has_prefix(this_file):
            return this_file.name.startswith(file_prefix)
        
        return list(filter(file_has_prefix, all_files))
    
    async def get_dir(self, file_prefix, local_path):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        dir_files = await self.list_dir(file_prefix)
        for dir_file in dir_files:
            file_content = await self.get(dir_file.path)
            local_path = os.path.join(local_path, dir_file.name)
            
            async with aiofiles.open(local_path, 'wb') as local_file:
                await local_file.write(file_content)

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
            response = await requests.get(get_url, timeout=500)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"File download failed: {e}") from e
        
        return response.text
    
    def get_event_bus(self):
        return self._event_bus

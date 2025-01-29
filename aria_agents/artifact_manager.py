import httpx

class ArtifactManager:
    def __init__(self, event_bus=None):
        self.storage = {}
        self._svc = None
        self._artifact_id = None
        self.user_id = None
        self.session_id = None
        self._event_bus = event_bus

    async def setup(self, server, user_id, session_id, service_id="public/artifact-manager"):
        self._svc = await server.get_service(service_id)
        self.user_id = user_id
        self.session_id = session_id
        self._artifact_id = f"ws-user-{user_id}/aria-agents-chats:{session_id}"

    async def put(self, value, name):
        assert self._svc, "Please call `setup()` before using artifact manager"
        
        # Artifact has to be staged before we can put files
        try:
            artifact_info = await self._svc.read(artifact_id=self._artifact_id)
            await self._svc.edit(artifact_id=self._artifact_id, manifest=artifact_info.manifest)
            put_url = await self._svc.put_file(
                artifact_id=self._artifact_id,
                file_path=name
            )
            async with httpx.AsyncClient() as client:
                response = await client.put(put_url, data=value, timeout=500)
            response.raise_for_status()
        except Exception as e:
            print(f"File upload failed: {e}")
            raise RuntimeError(f"File upload failed: {e}") from e
        
        self._svc.commit(self._artifact_id)
        
        self._event_bus.emit("store_put", name)
        return name

    async def get_url(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        get_url = await self._svc.get_file(
            artifact_id=self._artifact_id,
            file_path=name
        )
        return get_url

    async def get(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        get_url = await self.get_url(name)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(get_url, timeout=500)
            response.raise_for_status()
        except Exception as e:
            print(f"File download failed: {e}")
            raise RuntimeError(f"File download failed: {e}") from e
        
        return response.text
    
    async def get_attachments(self):
        assert self._svc, "Please call `setup()` before using artifact manager"
        try:
            artifact_info = await self._svc.read(artifact_id=self._artifact_id)
            return artifact_info.manifest.get("attachments", [])
        except Exception as e:
            print(f"Failed to get attachments: {e}")
        
    async def get_attachment(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        attachments = await self.get_attachments()
        reversed_attachments = attachments[::-1] # Reverse order to get the latest attachment first
        for attachment in reversed_attachments:
            if attachment["name"] == name:
                return attachment
        return None
    
    def get_event_bus(self):
        return self._event_bus

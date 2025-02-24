import httpx
from aria_agents.server import get_server


class AriaArtifacts:
    def __init__(self, server=None, event_bus=None):
        self.server = server
        self._event_bus = event_bus
        self._svc = None
        self._artifact_id = None
        self.user_id = None
        self.session_id = None

    async def setup(
        self, token, user_id, session_id, service_id="public/artifact-manager"
    ):
        server_url = self.server.config.public_base_url
        self.server = await get_server(server_url, provided_token=token)
        self._svc = await self.server.get_service(service_id)
        self.user_id = user_id
        self.session_id = session_id
        self._artifact_id = f"ws-user-{user_id}/aria-agents-chats:{session_id}"

    async def put(self, value, name):
        assert self._svc, "Please call `setup()` before using artifact manager"

        # Artifact has to be staged before we can put files
        try:
            await self._svc.edit(artifact_id=self._artifact_id, version="stage")
            put_url = await self._svc.put_file(
                artifact_id=self._artifact_id, file_path=name
            )
            async with httpx.AsyncClient() as client:
                response = await client.put(put_url, data=value, timeout=500)
            response.raise_for_status()
        except Exception as e:
            print(f"File upload failed: {e}")
            raise RuntimeError(f"File upload failed: {e}") from e

        await self._svc.commit(self._artifact_id)

        self._event_bus.emit("store_put", name)
        return name

    async def get_url(self, name: str):
        assert self._svc, "Please call `setup()` before using artifact manager"
        get_url = await self._svc.get_file(
            artifact_id=self._artifact_id, file_path=name
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
        reversed_attachments = attachments[
            ::-1
        ]  # Reverse order to get the latest attachment first
        for attachment in reversed_attachments:
            if attachment["name"] == name:
                return attachment
        return None

    def get_event_bus(self):
        return self._event_bus

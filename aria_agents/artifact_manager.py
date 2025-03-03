import httpx
import datetime
from hypha_rpc.rpc import RemoteException
from aria_agents.server import get_server


class AriaArtifacts:
    def __init__(self, server=None, event_bus=None):
        self.server = server
        self._event_bus = event_bus
        self._svc = None
        self._artifact_id = None
        self.user_id = None
        self.session_id = None
        self._collection_alias = None
        self._collection_id = None
        self._workspace = None

    async def setup(
        self, token, user_id, session_id, service_id="public/artifact-manager"
    ):
        server_url = self.server.config.public_base_url
        self.server = await get_server(server_url, provided_token=token)
        self._svc = await self.server.get_service(service_id)
        self.user_id = user_id
        self.session_id = session_id
        self._workspace = f"ws-user-{user_id}"
        self._collection_alias = "aria-agents-chats"
        self._collection_id = f"{self._workspace}/{self._collection_alias}"
        self._artifact_id = f"{self._collection_id}:{session_id}"
        await self._try_create_collection()
        await self._try_create()

    async def _try_create_collection(self):
        galleryManifest = {
			"name": "Aria Agents Chat History",
			"description": "A collection used to store previous chat sessions with the Aria Agents chatbot",
			"collection": [],
		}

        try:
            await self._svc.create(
				type="collection",
				workspace=self._workspace,
				alias=self._collection_alias,
				manifest=galleryManifest,
			)
        except RemoteException as e:
            print(f"Collection couldn't be created. It likely already exists. Error: {e}")


    async def _try_create(self):
        try:
            await self._svc.create(
                type="chat",
                parent_id=self._collection_id,
                alias=f"{self._collection_alias}:{self.session_id}",
                manifest={
                    "id": self.session_id,
                    "name": "Aria agents chat",
                    "description": f"The Aria Agents chat history of {self.session_id}",
                    "type": "chat",
                    "conversations": [],
                    "artifacts": [],
                    "attachments": [],
                    "timestamp": datetime.datetime.now().isoformat(),
                    "userId": self.user_id,
                }
            )

        except RemoteException as e:
            print(f"Artifact couldn't be created. It likely already exists. Error: {e}")

    async def put_file(self, value, name):
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
        except RemoteException as e:
            print(f"File upload failed: {e}")
            raise RuntimeError(f"File upload failed: {e}") from e

        await self._svc.commit(self._artifact_id, version="new")

        self._event_bus.emit("store_put", name)
        return name
    
    async def add_vectors(self, vectors):
        assert self._svc, "Please call `setup()` before using artifact manager"
        try:
            # await self._svc.edit(artifact_id=self._artifact_id, version="stage")
            await self._svc.add_vectors(
                artifact_id=self._artifact_id, vectors=vectors
            )
        except Exception as e:
            print(f"Failed to add vectors: {e}")
            raise RuntimeError(f"Failed to add vectors: {e}") from e

        await self._svc.commit(self._artifact_id)

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
        except RemoteException as e:
            print(f"File download failed: {e}")
            raise RuntimeError(f"File download failed: {e}") from e

        return response.text

    async def get_attachments(self):
        assert self._svc, "Please call `setup()` before using artifact manager"
        try:
            artifact_info = await self._svc.read(artifact_id=self._artifact_id)
            return artifact_info.manifest.get("attachments", [])
        except RemoteException as e:
            print(f"Failed to get attachments: {e}")
            raise RuntimeError(f"Failed to get attachments: {e}") from e

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
    
    async def clear(self):
        assert self._svc, "Please call `setup()` before using artifact manager"
        return await self._svc.delete(
            artifact_id=self._artifact_id,
            delete_files=True,
            recursive=True
        )

    def get_event_bus(self):
        return self._event_bus

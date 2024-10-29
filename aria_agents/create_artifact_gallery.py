from hypha_rpc import connect_to_server

# TODO:
#   On login:
#   1. get_artifact_service
#   2. look for existing prefix f"collections/aria-agents-chats/{user_id}-chats"
#       if exists: continue to 3
#       else: create_artifact_dataset
#   3. get access to put_artifact_file and get_artifact_file
#   4. list items for sidebar
#
#   On chat message:
#   1. put_artifact_file f"collections/aria-agents-chats/{user_id}-chats/{session_id}"
#
#   On click sidebar history:
#   1. get_artifact_file f"collections/aria-agents-chats/{user_id}-chats/{session_id}"
async def get_artifact_service(server_url):
    server = await connect_to_server({"server_url": server_url})
    return await server.get_service("public/artifact-manager")

async def create_artifact_gallery(artifact_service):
    gallery_manifest = {
        "id": "aria-agents-chats",
        "name": "Aria Agents Chat History",
        "description": (
            "A collection used to store previous chats sessions with"
            "the Aria Agents chatbot"
        ),
        "type": "collection",
        "collection": [],
    }
    
    await artifact_service.create(
        prefix="collections/aria-agents-chats",
        manifest=gallery_manifest,
        orphan=True
    )

def main():
    artifact_service = get_artifact_service("hypha.aicell.io")
    create_artifact_gallery(artifact_service)

if __name__ == "__main__":
    main()
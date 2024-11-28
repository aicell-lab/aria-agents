import os
import dotenv
import asyncio
from hypha_rpc import connect_to_server
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

async def main():
    dotenv.load_dotenv()

    app = FastAPI(root_path="/aria-agents/apps/aria-agents-ui")

    static_dir = os.path.join(os.path.dirname(__file__), '../aria_agents/static')

    app.mount("/chat", StaticFiles(directory=static_dir), name="chat")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return FileResponse(os.path.join(static_dir, "index.html"))

    async def serve_fastapi(args, context=None):
        await app(args["scope"], args["receive"], args["send"])
    
    workspace_token = os.environ.get("WORKSPACE_TOKEN")
    server_url = "https://hypha.aicell.io"

    server = await connect_to_server({
        "server_url": server_url,
        "workspace": "aria-agents",
        "token": workspace_token
    })

    svc_info = await server.register_service({
        "id": "aria-agents-ui",
        "name": "Aria Agents UI",
        "type": "asgi",
        "serve": serve_fastapi,
        "config": {"visibility": "public"}
    })

    print(f"Access your app at: {server_url}/{server.config.workspace}/apps/{svc_info['id'].split(':')[1]}")
    
def test_frontend():
    asyncio.run(main())
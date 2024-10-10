import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from hypha_rpc import connect_to_server

app = FastAPI()

# Define FastAPI endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head><title>Aria Agents</title></head>
        <body><h1>Welcome to Aria Agents Service</h1></body>
    </html>
    """

@app.get("/api/v1/status")
async def status():
    return {"message": "Aria Agents Service is running."}

# Serve FastAPI app through Hypha's service registration
async def serve_fastapi(args, context=None):
    scope = args["scope"]
    print(f'{context["user"]["id"]} - {scope["client"]} - {scope["method"]} - {scope["path"]}')
    await app(args["scope"], args["receive"], args["send"])

async def main():
    # Connect to the existing Hypha server
    server = await connect_to_server({
        "server_url": "https://hypha.aicell.io",
        "workspace": "aria-agents",
        # Token or login for secure connection
        "login": True,  # or use "token": "your_token_here"
    })

    # Register the service under the specified workspace
    svc_info = await server.register_service({
        "id": "aria-agents-service",
        "name": "Aria Agents Service",
        "type": "asgi",
        "serve": serve_fastapi,
        "config": {"visibility": "public"}
    })

    print(f"Access your service at: {server.config.workspace}/apps/{svc_info['id'].split(':')[1]}")
    await server.serve()

# Run the main coroutine
asyncio.run(main())

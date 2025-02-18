import os
from hypha_rpc import connect_to_server, login


async def get_server(server_url, workspace_name=None, provided_token=None):
    login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    if login_required:
        token = (
            await login({"server_url": server_url})
            if provided_token is None
            else provided_token
        )
    else:
        token = None
    server = await connect_to_server(
        {
            "server_url": server_url,
            "token": token,
            "method_timeout": 500,
            **({"workspace": workspace_name} if workspace_name is not None else {}),
        }
    )
    return server

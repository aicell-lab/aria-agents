import asyncio
import os
from hypha_rpc import login

async def save_hypha_token(server_url):
    token = await login({"server_url": server_url})
    env_lines = []
    token_found = False

    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")

    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            env_lines = env_file.readlines()
    except FileNotFoundError:
        pass

    with open(env_path, "w", encoding="utf-8") as env_file:
        for line in env_lines:
            if line.startswith("TEST_HYPHA_TOKEN="):
                env_file.write(f"TEST_HYPHA_TOKEN={token}\n")
                token_found = True
            else:
                env_file.write(line)
        if not token_found:
            env_file.write(f"TEST_HYPHA_TOKEN={token}\n")
    
    print("Hypha test token has hopefully been written to .env!")

if __name__ == "__main__":
    asyncio.run(save_hypha_token("https://hypha.aicell.io"))

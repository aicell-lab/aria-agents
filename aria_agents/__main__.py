import sys
import argparse
import asyncio
import subprocess
import os
from dotenv import load_dotenv
from aria_agents.chatbot import connect_server

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'minio.env')
load_dotenv(dotenv_path)

def run_locally(args):
    # TODO: if server is running on {args.server_url}, then:
    #   connect_to_server(args)
    
    if args.login_required:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "true"
    else:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "false"
    # get current file path so we can get the path of apps under the same directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    command = [
        sys.executable,
        "-m",
        "hypha.server",
        f"--host={args.host}",
        f"--port={args.port}",
        f"--public-base-url={args.public_base_url}",
        f"--static-mounts=/chat:{current_dir}/static",
        "--enable-s3",
        f"--access-key-id={os.getenv('MINIO_ROOT_USER')}",
        f"--secret-access-key={os.getenv('MINIO_ROOT_PASSWORD')}",
        f"--endpoint-url={os.getenv('MINIO_SERVER_URL')}",
        f"--endpoint-url-public={os.getenv('MINIO_SERVER_URL')}",
        "--s3-admin-type=minio",
        "--startup-functions=aria_agents.chatbot:register_chat_service"
    ]
    subprocess.run(command)

def connect_to_server(args):
    if args.login_required:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "true"
    else:
        os.environ["BIOIMAGEIO_LOGIN_REQUIRED"] = "false"
    server_url = args.server_url
    loop = asyncio.get_event_loop()
    loop.create_task(connect_server(server_url))
    loop.run_forever()


def main():
    parser = argparse.ArgumentParser(description="BioImage.IO Chatbot utility commands.")
    
    subparsers = parser.add_subparsers()

    # Start server command
    parser_start_server = subparsers.add_parser("local")
    parser_start_server.add_argument("--server-url", type=str, default="0.0.0.0")
    parser_start_server.add_argument("--port", type=int, default=9000)
    parser_start_server.add_argument("--public-base-url", type=str, default="")
    parser_start_server.add_argument("--login-required", action="store_true")
    parser_start_server.set_defaults(func=run_locally)
    
    # Connect server command
    parser_connect_server = subparsers.add_parser("remote")
    parser_connect_server.add_argument("--server-url", default="https://ai.imjoy.io")
    parser_connect_server.add_argument("--login-required", action="store_true")
    parser_connect_server.set_defaults(func=connect_to_server)

    
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        
if __name__ == '__main__':
    main()
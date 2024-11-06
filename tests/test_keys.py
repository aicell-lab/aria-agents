import openai
from hypha_rpc.sync import connect_to_server
import os

def test_openai_api_key():
    OPENAI_API_KEY="sk-_Tza1hGuYlfzCcy0Gg3CttD5LFDDIuwGvb3a_EaVZ4T3BlbkFJ4RB06FZO_jspfXL7oJPjs0FUlzFsgHNaROcwAKizkA"
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    client.models.list()
    
def test_hypha_key():
    HYPHA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2FtdW4uYWkvIiwic3ViIjoiYmVzdC1nZXJhbml1bS0xMDU0ODA5MCIsImF1ZCI6Imh0dHBzOi8vYW11bi1haS5ldS5hdXRoMC5jb20vYXBpL3YyLyIsImlhdCI6MTczMDExMDYyNCwiZXhwIjoxNzYxNjQ2NjI0LCJzY29wZSI6IndzOmFyaWEtYWdlbnRzI3J3IHdpZDphcmlhLWFnZW50cyIsImd0eSI6ImNsaWVudC1jcmVkZW50aWFscyIsImh0dHBzOi8vYW11bi5haS9yb2xlcyI6W10sImh0dHBzOi8vYW11bi5haS9lbWFpbCI6Imh1Z28uZGV0dG5lckBzY2lsaWZlbGFiLnNlIn0.y6T-dFm6HAcW2JqDgOdDiWTmfvZ5X51GBCADLzfqxVk"
    connect_to_server({"server_url": "https://hypha.aicell.io", "token": HYPHA_TOKEN, "workspace": "aria-agents"})
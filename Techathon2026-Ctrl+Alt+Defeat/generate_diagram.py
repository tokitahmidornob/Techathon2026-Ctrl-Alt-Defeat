from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.programming.language import Python


with Diagram("Techathon2026 - System Architecture", show=False, filename="system_diagram"):
    
    boss = User("The Boss")
    staff = User("Office Staff")

    with Cluster("Simulated Office Environment (15 Devices)"):
        room1 = Server("Drawing Room\n(2 Fans, 3 Lights)")
        room2 = Server("Work Room 1\n(2 Fans, 3 Lights)")
        room3 = Server("Work Room 2\n(2 Fans, 3 Lights)")
        rooms = [room1, room2, room3]

    backend = Python("FastAPI Backend\n(Core Simulation & API)")

    with Cluster("User Interfaces"):
        web_ui = Server("Live Web Dashboard\n(Async Polling)")
        discord_bot = Python("Discord Bot\n(Gemini LLM Integration)")

    
    for r in rooms:
        r >> Edge(color="darkgreen", label="State Updates") >> backend


    backend >> Edge(color="blue", label="JSON REST Data") >> web_ui
    backend >> Edge(color="blue", label="Internal API Read") >> discord_bot


    web_ui >> Edge(label="Visualizes") >> boss
    discord_bot << Edge(color="purple", label="Commands (!status, !usage)") >> staff
    discord_bot << Edge(color="purple") >> boss
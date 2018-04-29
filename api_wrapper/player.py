import asyncio
from .server import Server

RESTARTS = 100

class Player():
    port = 8000
    def __init__(self, race, type, difficulty=None, server=None, server_route=None, server_address=None):
        self.race = race
        self.type = type
        self.difficulty = difficulty
        self.server = server
        self.isComputer = type == "Computer"
        if (not self.server) and (self.type != 'Computer'):
            port = Player.port
            for i in range(0, RESTARTS):
                port += 1
                print( port)
                self.server =  Server(server_route, server_address, str(port))
                loop = asyncio.get_event_loop()
                future = asyncio.Future()
                asyncio.ensure_future(self.server.start_server(future))
                try:
                    loop.run_until_complete(future)
                    Player.port = port
                    break
                except Exception:
                    pass
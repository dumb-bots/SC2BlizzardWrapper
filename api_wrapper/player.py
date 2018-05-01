import asyncio
from .server import Server
import portpicker

class Player():
    def __init__(self, race, type, difficulty=None, server=None, server_route=None, server_address=None):
        self.race = race
        self.type = type
        self.difficulty = difficulty
        self.server = server
        self.isComputer = type == "Computer"
        self.game_port = portpicker.pick_unused_port()
        self.base_port = portpicker.pick_unused_port()
        if (not self.server) and (self.type != 'Computer'):
            port = portpicker.pick_unused_port()
            self.server =  Server(server_route, server_address, str(port))
            loop = asyncio.get_event_loop()
            future = asyncio.Future()
            asyncio.ensure_future(self.server.start_server(future))
            loop.run_until_complete(future)
            Player.port = port
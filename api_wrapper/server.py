from multiprocessing import Process
from subprocess import Popen, PIPE, DEVNULL
import asyncio
import time
class Server():
    servers = []
    @staticmethod
    async def get_server(starcraft_route, address, port):
        for server in Server.servers:
            print(server.status)
            if server.status == "idle":
                server.status = "Busy"
                return server
        print(Server.servers)
        server = Server(starcraft_route, address, port)
        await server.start_server()
        server.status = "Busy"
        Server.servers.append(server)
        return server

    def __init__(self, starcraft_route, address, port):
        self.starcraft_route = starcraft_route
        self.address = address
        self.port = port
        self.status = 'stopped'
        self.process = None

    async def start_server(self):
        command = "{0}/Versions/Base55958/SC2_x64 --listen={1} --port={2}"
        command =  command.format(self.starcraft_route,
                self.address, self.port)
        p = Popen(command.split(" "), shell=False)
        time.sleep(7)
        if p.poll:
            self.status = "idle"
            self.process = p
        else:
            self.process = None
            self.status = "failed"

    def close(self):
        self.status = 'stopped'
        self.process.terminate()
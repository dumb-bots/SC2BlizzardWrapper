from multiprocessing import Process
from subprocess import Popen, PIPE, DEVNULL, STDOUT
import asyncio
import time
import io
import sys


class Server:
    # servers = []

    @staticmethod
    async def get_server(starcraft_route, address, port):
        # for server in Server.servers:
        #     print(server.status)
        #     if server.used > 2:
        #         server.process.terminate()
        #         server.status = "Terminated"
        #         continue
        #     if server.status == "idle":
        #         server.status = "Busy"
        #         server.used += 1
        #         return server
        # Server.servers = list(
        #     filter(lambda x: x.status != "Terminated", Server.servers)
        # )
        # print(Server.servers)
        server = Server(starcraft_route, address, port)
        await server.start_server()
        return server

    def __init__(self, starcraft_route, address, port):
        self.starcraft_route = starcraft_route
        self.address = address
        self.port = port
        self.status = "stopped"
        self.process = None
        # self.used = 0

    async def start_server(self):
        command = "{0}/Versions/Base55958/SC2_x64 --listen={1} --port={2}"
        # command = "{0}/Versions/Base60321/SC2_x64 --listen={1} --port={2}"
        command = command.format(self.starcraft_route, self.address, self.port)
        p = Popen(command.split(" "), shell=False, stdout=PIPE, stderr=STDOUT)
        count = 0
        while True:
            count += 1
            line = p.stdout.readline()
            print(str(count) + " " + str(line))
            if count == 9:
                self.status = "idle"
                self.process = p
                break

    def close(self):
        self.status = "stopped"
        self.process.terminate()

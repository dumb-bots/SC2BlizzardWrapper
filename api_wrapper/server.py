from multiprocessing import Process
from subprocess import Popen, PIPE, DEVNULL
import asyncio
import time
class Server():
    def __init__(self, starcraft_route, address, port):
        self.starcraft_route = starcraft_route
        self.address = address
        self.port = port
        self.status = 'stopped'
        self.process = ''

    async def start_server(self, future):
        command = "{0}/Versions/Base55958/SC2_x64 --listen={1} --port={2}"
        command =  command.format(self.starcraft_route,
                self.address, self.port)
        p = Popen(command.split(" "), shell=False)
        time.sleep(7)
        if( not p.poll()):
            future.set_result("Server started")
            self.status = "started"
            self.process = p
        else:
            future.set_exception(Exception("Server closed"))
            self.process = None
    def close():
        self.status = 'stopped'
        self.p.terminate()
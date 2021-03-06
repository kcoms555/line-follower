from threading import Thread
from runner import Runner
import asyncio
import websockets
import parse
import json
import math
from vector import get_vector_sum
from vector import get_vector_len
from vector import get_angle

PORT = 3003
	
runner = Runner(2)

def parse_msg(msg):
	result = parse.parse("{header}:::{body}", msg)
	return result['header'], result['body']

class UserStatus:
	def __init__(self, wscp):
		self.wscp = wscp
		self.adr = wscp.remote_address

	async def parse_and_execute(self):
		has_control = False
		while True:
			header, body = parse_msg(await self.recv())
			if header == 'MESSAGE':
				print(f"{self.adr[0]}:{self.adr[1]}이 보낸 메세지 : {body}")
			if header == 'RUN':
#				print(f"{self.adr[0]}:{self.adr[1]} RUN : {body}")
				data = json.loads(body)

				if data['release']:
					runner.release_control()
					has_control = False
					continue

				if not has_control:
					is_trying_to_control = False
					for i in data:
						if data[i]:
							is_trying_to_control = True
					if is_trying_to_control:
						has_control = runner.take_control()
					else:
						continue

				root2 = 2**(1./2)
				vector = (0, 0)
				degree_count = 0
				if data['1']:
					vector = get_vector_sum(vector, (-1/root2, -1/root2))
				if data['2']:
					vector = get_vector_sum(vector, (0, -1))
				if data['3']:
					vector = get_vector_sum(vector, (1/root2, -1/root2))
				if data['4']:
					vector = get_vector_sum(vector, (-1, 0))
				if data['5']:
					vector = get_vector_sum(vector, (0, 0))
				if data['6']:
					vector = get_vector_sum(vector, (1, 0))
				if data['7']:
					vector = get_vector_sum(vector, (-1/root2, 1/root2))
				if data['8']:
					vector = get_vector_sum(vector, (0, 1))
				if data['9']:
					vector = get_vector_sum(vector, (1/root2, 1/root2))
				if data['+']:
					runner.addspeed(1)
				if data['-']:
					runner.addspeed(-1)

				vectorlen = get_vector_len(vector)
				if vectorlen < 0.1:
					runner.stop()
				else:
					# 두 벡터 사이 각
					# 양수이면 (0,1)의 우측에 위치
					runner.setdegree( get_angle(vector, (0, 1)) )
					runner.go()
	async def send(self, msg):
		try:
			await self.wscp.send(msg)
		except websockets.exceptions.ConnectionClosed as e:
			print(f"send :: connection {self.adr[0]}:{self.adr[1]} closed {e.code}{e.reason}!")

	async def recv(self):
		return await self.wscp.recv()

	async def wait_closed(self):
		return await self.wscp.wait_closed()

	async def close(self, code, msg):
		await self.wscp.close(code, msg)


all_users = set();
async def accept(socket, path):
	try:
		user = UserStatus(socket)
		all_users.add(user);
		print(f"accept :: {user.adr[0]}:{user.adr[1]} connected")
		task = asyncio.create_task(user.parse_and_execute())
		await task
		await user.wait_closed()
		print(f"accept :: {user.adr[0]}:{user.adr[1]} closed")
	except asyncio.CancelledError as e:
		await user.send("cancelled error")
		await user.close(1001, "cancelled error")
		print("accepct :: Cancelled error")
	except websockets.exceptions.ConnectionClosed:
		print(f'accept :: {user.adr[0]}:{user.adr[1]} closed')
	finally:
		all_users.remove(user)

async def run_server():
	start_server = await websockets.serve(accept, "0.0.0.0", PORT);
	await start_server.wait_closed();

def server_main():
	try:
		asyncio.run(run_server())
	except KeyboardInterrupt:
		print('server KeyboardInterrupt')

server_thread = None
def run(port = 3003):
	global server_thread
	PORT = port
	server_thread = Thread(target = server_main, daemon=True)
	server_thread.start()

if __name__ == '__main__':
	try:
		run()
		server_thread.join()
	finally:
		runner.cleanup()

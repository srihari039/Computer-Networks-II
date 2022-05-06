import socket
import threading
import time
import sys
import os
import pickle
from blockchain import *

HEADER_SIZE = 1024*64
HAND_SHAKE = 'hand_shake'
REQUEST_CHECK = 'request_check'
SEND_CHECK = 'send_check'
SEND_CHAIN = 'send_chain'
REQUEST_CHAIN = 'request_chain'
REQUEST_INFO = 'request_info'
SEND_INFO = 'send_info'
REPLACE_CHAIN = 'replace_chain'
CREATE_VOTE = 'create_vote'
UPDATED_CHAIN = 'updated_chain'

HOST = '127.0.0.1'
PORT = 50003
MY_ADDRESS = (HOST,PORT)
peers = [(HOST,PORT-3)]
checking = False
checked = []
check = []

original_chain = block_chain()

# print(len(temp_chain.chain))

class peer_s:
	def __init__(self):		
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.Address = (HOST,PORT)
		self.server.bind(self.Address)
		self.server.listen()
		self.difficulty = None
		self.update_blocks = {}
		self.temp_chain = block_chain()
		self.temp_chain.chain = []
		self.all_chains = {}
		self.updates = 0

	def most_common(self,lst):
		return max(set(lst), key=lst.count)

	def listen_from_peer(self,client,address):
		port_no = int(client.recv(HEADER_SIZE).decode('utf-8'))
		peer = (address[0],port_no)
		if peer == MY_ADDRESS:
			return
		if peer not in peers:
			peers.append(peer)
			peer_c_.connect_all_peers()
		while True:
			try:
				message = client.recv(HEADER_SIZE).decode('utf-8')
				if message == '':
					continue
				if UPDATED_CHAIN in message:
					# client.send(REQUEST_CHAIN.encode('utf-8'))
					peer_c_.broadcast_message(REQUEST_CHAIN)
				if HAND_SHAKE in message:
					message = message.split(' ')
					peer = (message[1],int(message[2]))
					if peer not in peers and peer != MY_ADDRESS:
						# print(peer)
						peers.append(peer)
						peer_c_.connect_all_peers()

				elif SEND_INFO in message:
					data = client.recv(HEADER_SIZE)
					data = pickle.loads(data)
					self.difficulty = data
					# print(data)
				elif REQUEST_INFO in message:
					client.send(SEND_INFO.encode('utf-8'))
					data = pickle.dumps(self.difficulty)
					client.send(data)
				elif REQUEST_CHAIN in message:
					# print('Chain requested')
					# print(f'Original votes : {len(original_chain.chain)-1}')
					time.sleep(0.5)
					for i in range(0,len(original_chain.chain)):
						peer_c_.broadcast_message(SEND_CHAIN)
						data = [original_chain.chain[i],i == len(original_chain.chain)-1]
						peer_c_.broadcast_data(data)
						time.sleep(0.5)
					# print('sent the chain!')

				elif SEND_CHAIN in message:
					data = client.recv(HEADER_SIZE)
					data_ = pickle.loads(data)
					block_,finished = data_
					if not finished:
						if client not in self.all_chains:
							self.all_chains[client] = [block_]
						else:
							self.all_chains[client].append(block_)
						self.temp_chain.chain.append(block_)
					else:
						self.all_chains[client].append(block_)
						self.temp_chain.chain.append(block_)
						self.updates += 1
					# print(self.updates,len(peers))
					if self.updates == len(peers):
						chains = [self.all_chains[key] for key in self.all_chains]
						chains = [list(set(chain)) for chain in chains]						
						# print(f'lc : {len(chains)}')
						# print(118)
						# chain = self.most_common(chains)
						chain = []
						try:
							chain = max(set(chains),key=chains.count)
						except:
							for chain_ in chains:
								# print('here')
								if len(chain) < len(chain_):
									chain = chain_
						chain.sort(key = lambda x : x.timestamp)
						chain_ = []
						filtering ={}
						for c in chain:
							# print(c.timestamp)
							if c.timestamp in filtering:
								continue
							else:
								filtering[c.timestamp] = True
								chain_.append(c)
						original_chain.chain = chain_
						# original_chain.chain = chain
						self.all_chains = {}
						self.updates = 0
						self.temp_chain = block_chain()
						self.temp_chain.chain = []
						# print('Chain updated')
						# print('total vote count - ',len(original_chain.chain)-1)

				elif SEND_CHECK in message:
					data = client.recv(HEADER_SIZE)
					data = pickle.loads(data)
					if checking:
						check.append(data)
				elif REQUEST_CHECK in message:
					client.send(SEND_CHECK.encode('utf-8'))
					data = [original_chain.get_last_block(),original_chain.difficulty]
					data = pickle.dumps(data)
					client.send(data)

				elif CREATE_VOTE in message:
					data = client.recv(HEADER_SIZE)
					data = pickle.loads(data)
					# original_chain.cast_vote(data)
					original_chain.chain.append(data)

				elif REPLACE_CHAIN in message:
					data = client.recv(HEADER_SIZE)
					data = pickle.loads(data)
					new_block, new_diff = data

					votes_local_copy = [vote for vote in original_chain.votes]
					votes_foreign_copy = [vote for vote in new_block.votes]

					length = len(votes_foreign_copy)

					if new_block.previous_hash != original_chain.get_last_block().previous_hash:
						for i in range(length):
							index = None
							try:
								index = votes_local_copy.index(votes_foreign_copy[0])
							except:
								index = -1
							if index == -1:
								break
							
							votes_local_copy.pop(index)
							votes_foreign_copy.pop(0)

						check1 = False
						check2 = False

						proposed_length = len(votes_foreign_copy)
						is_valid_votes = block.is_valid(original_chain)
						valid_hash = original_chain.get_last_block().hash == new_block.previous_hash
						check = new_diff == original_chain.difficulty - 2 or original_chain.difficulty + 1
						valid_time = new_block.timestamp < datetime.timestamp(datetime.now())
						check1 = proposed_length != 0 and is_valid_votes and valid_hash and check and valid_time


						is_in_checked = [new_block.previous_hash, original_chain.chain[len(original_chain.chain)-2].timestamp or ""] in checked
						check2 = not is_in_checked

						if check1:
							original_chain.chain.append(new_block)
							original_chain.difficulty = new_diff
							original_chain.votes = [vote for vote in votes_local_copy]

						elif check2:
							checked.append([original_chain.get_last_block().previous_hash,original_chain[len(original_chain.chain)-2].timestamp or ""])
							position = len(original_chain.chain)-1
							checking = True

							client.send(REQUEST_CHECK.encode('utf-8'))
							most_appeared = check[0]

							time.sleep(5)

							for entry in check:
								pass

							group = most_appeared
							original_chain.chain[position] = group[0]
							original_chain.difficulty = group[1]

							check = check[len(check):]
					pass
				# print(f'message : {message}')
			except:
				pass
				# print('--')
				# client.close()

	def recieve_from_peer(self):
		while True:
			client,address = self.server.accept()
			# if (client,address) in self.connected:
			# 	continue
			
			thread = threading.Thread(target=self.listen_from_peer, args=(client,address))
			thread.start()

class peer_c:
	def __init__(self):
		self.connected = []
		self.peers_ = []

	def connect_all_peers(self):
		# print(f'No.of peers : {len(peers)}')
		for peer in peers:
			if peer not in self.connected:
				server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				server.connect(peer)
				self.connected.append(peer)
				self.peers_.append(server)
				thread = threading.Thread(target=self.communicate_with_peer,args=(server,))
				thread.start()

	def broadcast_message(self,message):
		message = message.encode('utf-8')
		for server in self.peers_:
			try:
				server.send(message)
			except:
				pass
				# print(f'server : {server} is down')
	def broadcast_data(self,data):
		data = pickle.dumps(data)
		for server in self.peers_:
			try:
				server.send(data)
			except:
				pass
				# print(f'server : {server} is down')

	def check_new_connections(self):
		# while True:
		# time.sleep(4)
		self.connect_all_peers()

	def send_new_peer_list(self,server):
		self.sent = []
		while True:
			# time.sleep(20)
			if len(peers) >= 2:
				address = HAND_SHAKE+' '+peers[-1][0]+' '+str(peers[-1][1])
				# print(f'Sending address to {server}')
				try:
					if server not in self.sent:
						time.sleep(0.5)
						server.send(address.encode('utf-8'))
						self.sent.append(server)
					else:
						pass
				except:
					# print(f'server {server} temporarily down')
					return

	def communicate_with_peer(self,server):
		server.send(str(PORT).encode('utf-8'))
		thread = threading.Thread(target=self.send_new_peer_list,args=(server,))
		thread.start()
		# while True:
		# 	message = input(':::')
		# 	server.send(message.encode('utf-8'))

peer_c_ = peer_c()
thread = threading.Thread(target = peer_c_.check_new_connections)
thread.start()

peer_s_ = peer_s()
thread = threading.Thread(target=peer_s_.recieve_from_peer)
thread.start()

user_ = None


def cast_vote():
	global user_
	mode = input()
	if mode == 'console':
		while True:
			opt = input('Enter [1-cast_vote] [2-leaderboard] : ')
			if opt == '1':
				if user_ == None:
					user_ = user()
				else:
					print('user already voted')
					continue
				
				publickey = input('Enter public key : ')
				option = input('choose_option : ')
				user_.choose_option(option)

				new_vote = vote(user_.user_public_key, user_.option_pub)
				private_key = input('Enter private key for signing : ')
				new_vote.sign(user_.user_key_pair)

				peer_c_.broadcast_message(REQUEST_CHAIN)
				time.sleep(3)
				original_chain.cast_vote(new_vote)
				peer_c_.broadcast_message(CREATE_VOTE)
				peer_c_.broadcast_data(original_chain.chain[-1])
				cast_vote()
			else:
				peer_c_.broadcast_message(REQUEST_CHAIN)
				time.sleep(3)
				# peer_c_.broadcast_message()
				print('Leaderboard')
				print('Votes casted - ',len(original_chain.chain)-1)
				original_chain.calculate_votes(candidates_)
				cast_vote()
			# print('last-hash --> ',original_chain.chain[-1].hash)
	else:
		cast_vote()


# time.sleep(3)
thread = threading.Thread(target = cast_vote)
thread.start()
# peer_s_ = peer_s()
# thread = threading.Thread(target=peer_s_.recieve_from_peer)
# thread.start()

# peer_c_ = peer_c()
# thread = threading.Thread(target = peer_c_.check_new_connections)
# thread.start()

# time.sleep(5)
# peer_c_.broadcast_message(REQUEST_CHAIN)

# time.sleep(2)
# print((original_chain.chain[-1].hash))

# time.sleep(5)
# print(len(original_chain.chain))

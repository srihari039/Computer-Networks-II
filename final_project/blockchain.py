import hashlib as hasher
from datetime import datetime
from ecdsa import SigningKey, VerifyingKey, SECP256k1
import pprint

class candidates:
	def __init__(self):
		self.candidA_private_key = b"\x01\xb0U'm\x11!\x02\xb6>}\xe50\xfb\x8c\xbaD0\x94KE\x87\xbe\xd3\x88\xc2h\n'.\xc3\xf6"
		self.candidB_private_key = b"\x9a'-\xe2\x8d<\xe2*~\x03xG\x114x \xc6\xa17d\x96+\\<\xd0\xfaz\x89\x07\xf7z\xb3"
		self.candidC_private_key = b'\x82*}\x11VbA\x84\xc3&\xe3\xe1\xa4\x89D\xf0QcS\x86O\x8dg\xb2\x0f\x97\x81Q2\xc7Kv'
		self.candidD_private_key = b'p\xc0\x1f\xfa\x12\x9f\xe4\xae\x8c\x153k;\xbf\xc2\xad]\xd8S\xd6-0\x86\xf35\x93]59\xa5\x10/'
		self.nota_private_key = b'e\x1c\xf8\x01\x83\xa0\xec\xf6\x0f{9\xf6\xc7\xf3\xf0\x81!\xf5:i!!?\xa3&\xa8\xb3\x1d\x82\xfc,\xed'

	def get_key_pair(self,option):
		if option == "candidA":
			signing_Key = SigningKey.from_string(self.candidA_private_key,curve=SECP256k1)
			verifying_key = SigningKey.get_verifying_key(signing_Key)
			return signing_Key,verifying_key
		elif option == "candidB":
			signing_Key = SigningKey.from_string(self.candidB_private_key,curve=SECP256k1)
			verifying_key = SigningKey.get_verifying_key(signing_Key)
			return signing_Key,verifying_key
		elif option == "candidC":
			signing_Key = SigningKey.from_string(self.candidC_private_key,curve=SECP256k1)
			verifying_key = SigningKey.get_verifying_key(signing_Key)
			return signing_Key,verifying_key
		elif option == "candidD":
			signing_Key = SigningKey.from_string(self.candidD_private_key,curve=SECP256k1)
			verifying_key = SigningKey.get_verifying_key(signing_Key)
			return signing_Key,verifying_key
		else:
			signing_Key = SigningKey.from_string(self.nota_private_key,curve=SECP256k1)
			verifying_key = SigningKey.get_verifying_key(signing_Key)
			return signing_Key,verifying_key
		
	def get_candidate_from_key(self,key):
		public_key_candidate = VerifyingKey.from_string(bytes.fromhex(key), curve=SECP256k1)
		if public_key_candidate == self.get_key_pair("candidA")[1]:
			return "candidA"
		elif public_key_candidate == self.get_key_pair("candidB")[1]:
			return "candidB"
		elif public_key_candidate == self.get_key_pair("candidC")[1]:
			return "candidC"
		elif public_key_candidate == self.get_key_pair("candidD")[1]:
			return "candidD"
		else:
			return "nota"

class block:
	def __init__(self, index, timestamp, data, previous_hash,vote_count={}):
		self.index = index
		self.timestamp = timestamp
		self.data = data
		self.previous_hash = previous_hash
		self.nonce = 0
		self.vote_count = vote_count
		self.hash = self.hash_block()
		# print(self.hash)

	# generate a key pair from ecc algorithms
	@staticmethod
	def generate_key_pair():
		sk = (SigningKey.generate(curve=SECP256k1))
		vk = (sk.get_verifying_key())
		return (sk, vk)

	def hash_block(self):
		sha = hasher.sha256()
		string_to_hash = str(self.index) + str(self.timestamp) + str(self.data) + str(self.previous_hash) + str(self.nonce) #+ str(self.vote_count)
		sha.update(string_to_hash.encode('utf-8'))
		return sha.hexdigest()

	def mine(self,difficulty=0):
		while not self.hash.startswith('0'*difficulty):
			self.nonce += 1
			self.hash = self.hash_block()
		print("Vote successfully casted!")
		print("votes remaining - 0")

mint_key_pair = block.generate_key_pair()
mint_public_key = mint_key_pair[1]
holder_key_pair = block.generate_key_pair()

class block_chain:
	def __init__(self):
		self.chain = []
		self.initial_vote = vote(mint_public_key, holder_key_pair[1])
		self.create_genesis_block()
		self.difficulty = 1
		self.block_time = 3e3
		self.votes = []
		self.voters = []
	
	def create_genesis_block(self):
		self.chain.append(block(0, 1e7, self.initial_vote, "0"))

	def get_last_block(self):
		return self.chain[-1]

	def is_voted(self,address):
		for i in range(1,len(self.chain)):
			indi_block = self.chain[i]
			if address == indi_block.data.voter:
				return True
		return False

	def add_block(self, block, vote_):
		previous_block = self.get_last_block()
		block.previous_hash = previous_block.hash
		previous_vote_counts = previous_block.vote_count.copy()
		key = str(vote_.option.to_string().hex())
		if key in previous_vote_counts:
			previous_vote_counts[key] += 1
		else:
			previous_vote_counts[key] = 1

		block.vote_count = previous_vote_counts
		# self.calculate_votes(candidates_)
		block.hash = block.hash_block()
		block.mine(self.difficulty)

		self.difficulty += 2 if datetime.timestamp(datetime.now()) - previous_block.timestamp > self.block_time else -1
		self.chain.append(block)
		# self.calculate_votes(candidates_)
	def can_add_vote(self, vote_):
		vote_.voted = self.is_voted(vote_.voter)
		if vote_.is_valid():
			self.votes.append(vote_)
			vote_.voted = True
			return True
		else:
			return False

	def mine_vote(self, vote_):
		if len(self.votes) > 0: 
			self.add_block(block(len(self.chain), datetime.timestamp(datetime.now()), self.votes[0], self.get_last_block().hash),vote_)
			self.voters.append(vote_.voter)
		self.votes = []

	def is_chain_valid(self):
		for i in range(1, len(self.chain)):
			current_block = self.chain[i]
			previous_block = self.chain[i-1]
			if current_block.hash != current_block.hash_block() or current_block.previous_hash != previous_block.hash:
				return False
		return True

	def get_voting_details(self, voter_address):
		already_voted = False
		for i in range(1, len(self.chain)):
			current_block = self.chain[i]
			if voter_address == current_block.data.voter:
				already_voted = True
		return f"Voter: {voter_address}\nVoted: {already_voted}"

	def cast_vote(self,vote_):
		is_vote_valid = self.can_add_vote(vote_)
		if(is_vote_valid):
			self.mine_vote(vote_)
		return is_vote_valid

	def calculate_votes(self,candidates_):
		last_block = self.chain[-1]
		votes_count = last_block.vote_count.copy()
		
		leader_board = {}

		for key in votes_count:
			candidate = candidates_.get_candidate_from_key(key)
			if candidate in leader_board:
				leader_board[candidate] += votes_count[key]
			else:
				leader_board[candidate] = votes_count[key]

		pprint.pprint(leader_board)
		
class vote:
	def __init__(self, voter, candidate, voted=False): 
		self.voter = voter
		self.option = candidate
		self.voted = voted

	def sign(self,keypair):
		if keypair[1] == self.voter:
			self.signature = keypair[0].sign(str.encode(self.option.to_string().hex()), hashfunc=hasher.sha256)
		return

	def is_valid(self):
		check1 = self.voter and self.option and not self.voted
		check2 = self.voter.verify(self.signature, str.encode(self.option.to_string().hex()), hashfunc=hasher.sha256)
		return check1 and check2

class user:
	def __init__(self):
		self.user_key_pair = block.generate_key_pair()
		self.user_public_key = self.user_key_pair[1]
		self.user_private_key = self.user_key_pair[0]
		self.option_pub = None
		self.option_pri = None

	def choose_option(self, option):
		if option == 'a' or option == 'A':
			self.option_pri,self.option_pub = candidates_.get_key_pair("candidA")
		elif option == 'b' or option == 'B':
			self.option_pri,self.option_pub = candidates_.get_key_pair("candidB")
		elif option == 'c' or option == 'C':
			self.option_pri,self.option_pub = candidates_.get_key_pair("candidC")
		elif option == 'd' or option == 'D':
			self.option_pri,self.option_pub = candidates_.get_key_pair("candidD")
		else:
			self.option_pri,self.option_pub = candidates_.get_key_pair("nota")

candidates_ = candidates()
# bc = block_chain()
# user_ = user()
# user_.choose_option('a')

# new_vote = vote(user_.user_public_key, user_.option_pub)
# new_vote.sign(user_.user_key_pair)

# print(bc.get_voting_details(user_.user_public_key))
# bc.cast_vote(new_vote)

# # bc.calculate_votes(candidates_)
# user_ = user()
# user_.choose_option('b')

# new_vote = vote(user_.user_public_key, user_.option_pub)
# new_vote.sign(user_.user_key_pair)

# print(bc.get_voting_details(user_.user_public_key))
# bc.cast_vote(new_vote)

# bc.calculate_votes(candidates_)


















# new_vote = vote(user_.user_public_key, user_.option_pub)
# new_vote.sign(user_.user_key_pair)

# print(bc.get_voting_details(user_.user_public_key))
# bc.cast_vote(new_vote)

# user_ = user()
# user_.choose_option('a')
# new_vote = vote(user_.user_public_key, user_.option_pub)
# new_vote.sign(user_.user_key_pair)

# print(bc.get_voting_details(user_.user_public_key))
# bc.cast_vote(new_vote)
# get a key pair from secp256k1
# key_pair = block.generate_key_pair()

# # convert the private key to string
# private_key = key_pair[0].to_string().hex()

# print(private_key)

# # convert the private_key to signingkey object
# # signing_key = SigningKey.from_string(bytes(private_key,encoding='utf-8'),curve=SECP256k1)
# signing_Key = SigningKey.from_string(candidates_.candidateA[0].to_string(),curve=SECP256k1)

# print(candidates_.candidateA[0] == signing_Key)
# # convert the public key to string
# public_key = key_pair[1].to_string().hex()

# convert the public key to verifyingkey object
# verifying_key = VerifyingKey.from_string(bytes(public_key,encoding='utf-8'),curve=SECP256k1)
# print(verifying_key == key_pair[1])

# print(key_pair[0] == signing_key)

# convert string to verifying key using secp256k1
# vk = VerifyingKey.from_string(bytes.fromhex(pub_key), curve=SECP256k1)



# gf_wallet = block.generate_key_pair()

# # get key pair from private key using ecdsa curves
# # gf_wallet_ = ecdsa.SigningKey.from_string(bytes.fromhex(gf_wallet[1].to_string().hex()), curve=ecdsa.SECP256k1)
# gg = SigningKey.get_verifying_key(gf_wallet[0])
# print(gf_wallet[1] == gg)

# new_vote = vote(holder_key_pair[1], gf_wallet[1])
# new_vote.sign(holder_key_pair)

# print(bc.get_voting_details(holder_key_pair[1]))
# bc.cast_vote(new_vote)

# new_vote = vote(holder_key_pair[1], gf_wallet[1])
# new_vote.sign(holder_key_pair)
# print(bc.get_voting_details(holder_key_pair[1]))

# bc.cast_vote(new_vote)

# print(bc.get_voting_details(holder_key_pair[1]))
# new_vote_1 = vote(holder_key_pair[1], gf_wallet[1])
# new_vote_1.sign(holder_key_pair)

# bc.cast_vote(new_vote_1)

# gg = block.generate_key_pair()
# # new_vote = vote(holder_key_pair[1],gg[1])
# new_vote = vote(gg[1],gf_wallet[1])
# new_vote.sign(gg)

# print(bc.get_voting_details(gg[1]))
# bc.cast_vote(new_vote)

# hh = block.generate_key_pair()
# new_vote = vote(hh[1],gf_wallet[1])
# new_vote.sign(hh)

# print(bc.get_voting_details(hh[1]))
# bc.cast_vote(new_vote)


# if __name__ == '__main__':
# 	bc = block_chain()
# 	bc.add_block(block(1, datetime.timestamp(datetime.now()), "First Block", "0"))
# 	bc.add_block(block(2, datetime.timestamp(datetime.now()), "Second Block", "0"))
# 	bc.add_block(block(3, datetime.timestamp(datetime.now()), "Third Block", "0"))

# print(datetime.timestamp(datetime.now()))

# class candidates:
# 	def __init__(self):
# 		self.candidateA = block.generate_key_pair()
# 		self.candidateB = block.generate_key_pair()
# 		self.candidateC = block.generate_key_pair()
# 		self.candidateD = block.generate_key_pair()
# 		self.nota = block.generate_key_pair()
# 		print(self.candidateA[0].to_string())
# 		print(self.candidateB[0].to_string())
# 		print(self.candidateC[0].to_string())
# 		print(self.candidateD[0].to_string())
# 		print(self.nota[0].to_string())
		# print(self.candidateB[0].to_string().hex())
		# print(self.candidateC[0].to_string().hex())
		# print(self.candidateD[0].to_string().hex())
		# print(self.nota[0].to_string().hex())
from Blockchain.Backend.Core.blockheader import BlockHeader
from Blockchain.Backend.Core.block import Block
from Blockchain.Backend.Core.Database.database import BlockchainDB
from Blockchain.Backend.Util.util import hash256
from Blockchain.Backend.Core.tx import CoinbaseTx
import time
import json

from Blockchain.config import VERSION, TARGET, ZERO_HASH

class Blockchain:
    def __init__(self):
        # self.chain = []
        self.blockchainDB = BlockchainDB()

        if not self.blockchainDB.BlockchainDBExists():
            print("Blockchain database not found. Creating genesis block...")
            self.create_genesis_block()

    def write_on_disk(self, block):
        self.blockchainDB.write(block)

    def read_from_disk(self):
        return self.blockchainDB.read()

    def get_last_block(self):
        return self.blockchainDB.lastBlock()

    def create_genesis_block(self):
        self.add_block(1, ZERO_HASH)

    def convert_to_json(self):
        self.TxJson = []
        for tx in self.addTransactionsInBlock:
            self.TxJson.append(tx.to_dict())

    def add_block(self, blockHeight, prevBlockHash):

        # Create a new block header
        version = VERSION
        timestamp = int(time.time())
        bits = "ffff0000" # Placeholder for the actual difficulty target

        # transactions = []  # Placeholder for actual transactions
        # Txs = [f"A is sending {blockHeight} coins to B"]  # Placeholder for actual transactions
        # Create a coinbase transaction for the miner
        coinbase_tx = CoinbaseTx(blockHeight).CoinbaseTransaction()
        Txs = [coinbase_tx]

        # merkle_root = hash256(json.dumps(Txs).encode('utf-8'))
        merkle_root = ''

        block_header = BlockHeader(version, prevBlockHash, merkle_root, timestamp, bits)

        block_header.mine(TARGET)

        # Create a new block
        new_block = Block(blockHeight, 1, block_header.__dict__, Txs[0].to_dict()).__dict__

        # Add the new block to the blockchain
        # self.chain.append(new_block)
        # self.convert_to_json()
        self.write_on_disk([new_block])

        print(f"Block {blockHeight} added to the blockchain with hash: {block_header.blockHash}")

    def add_next_block(self):
        last_block = self.get_last_block()
        new_block_height = last_block["Height"] + 1
        new_prev_hash = last_block["BlockHeader"]["blockHash"]
        self.add_block(new_block_height, new_prev_hash)

    def print(self):
        print(json.dumps(self.read_from_disk(), indent=4))

    def validate_chain(self, chain=None):
        """
        Validates the integrity of the blockchain according to the lab requirements:
        
        1. Return False if the blockchain is empty.
        2. Check that the first block has height 1 and uses ZERO_HASH as its previous hash.
        3. Check that each block has the correct height and previous-block hash.
        4. Recalculate each block's hash and compare it with the stored hash.
           *Note*: The mining code increments the nonce after calculating the hash,
           so the nonce used for hashing was (stored_nonce - 1).
        5. Check that each block's hash satisfies the mining target (TARGET).
        
        Parameters:
            chain (list, optional): Blockchain data to validate. If None, reads from disk.
            
        Returns:
            bool: True if all blocks pass all checks; False otherwise.
        """
        # If no chain is explicitly passed, read the current chain from disk
        if chain is None:
            chain = self.read_from_disk()

        # Requirement 1: Return False if the blockchain is empty or not found
        if not chain or len(chain) == 0:
            return False

        # Requirement 2: Check first block (Genesis Block) height is 1 and previous hash is ZERO_HASH
        genesis_block = chain[0]
        if genesis_block.get("Height") != 1:
            return False

        genesis_header = genesis_block.get("BlockHeader", {})
        if genesis_header.get("prev_block_hash") != ZERO_HASH:
            return False

        # Iterate through every block in the blockchain to verify integrity
        for i in range(len(chain)):
            current_block = chain[i]
            current_header = current_block.get("BlockHeader", {})

            # Requirement 3a: Check that each block has the correct height
            expected_height = i + 1
            if current_block.get("Height") != expected_height:
                return False

            # Requirement 3b: Check previous-block hash linkage for all blocks after Genesis
            if i > 0:
                prev_block = chain[i - 1]
                prev_header = prev_block.get("BlockHeader", {})
                if current_header.get("prev_block_hash") != prev_header.get("blockHash"):
                    return False

            # Requirement 4: Recalculate each block's hash and compare with the stored hash.
            # IMPORTANT: In BlockHeader.mine(), the loop does:
            #   self.blockHash = hash256(...)
            #   self.nonce += 1
            # Therefore, the nonce saved in the block header is 1 greater than the nonce
            # that actually satisfied the hash during mining.
            stored_nonce = current_header.get("nonce", 0)
            actual_nonce = stored_nonce - 1

            version = current_header.get("version")
            prev_block_hash = current_header.get("prev_block_hash")
            merkle_root = current_header.get("merkle_root", "")
            timestamp = current_header.get("timestamp")
            bits = current_header.get("bits")

            # Reconstruct the exact string serialized during mine()
            serialized_header = (
                str(version) +
                str(prev_block_hash) +
                str(merkle_root) +
                str(timestamp) +
                str(bits) +
                str(actual_nonce)
            )

            recalculated_hash = hash256(serialized_header.encode('utf-8'))
            stored_hash = current_header.get("blockHash")

            # Compare recalculated hash with stored hash
            if recalculated_hash != stored_hash:
                return False

            # Requirement 5: Check that each block's hash satisfies the mining target (TARGET)
            if stored_hash[0:len(TARGET)] != TARGET:
                return False

        # If all checks pass for all blocks, the blockchain is valid
        return True

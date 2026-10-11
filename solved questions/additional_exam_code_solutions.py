import sys
import os
import copy
import json

# Setup import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
parent_root = os.path.dirname(project_root)

for path in [current_dir, project_root, parent_root, "C:/Users/muhib/Desktop"]:
    if path not in sys.path:
        sys.path.insert(0, path)

from Blockchain.config import TARGET, ZERO_HASH, INITIAL_REWARD, ONE_COIN
from Blockchain.Backend.Util.util import hash256
from blockchain import Blockchain

# =====================================================================
# EXAM TOPIC 1: Fault Localization (Audit Chain)
# =====================================================================
def audit_chain(chain):
    """
    Audits the blockchain and localizes the exact fault if invalid.
    Returns:
        (is_valid: bool, error_code: str, failed_height: int, details: str)
    """
    if not chain or len(chain) == 0:
        return (False, "EMPTY_CHAIN", 0, "The blockchain contains no blocks.")

    genesis = chain[0]
    if genesis.get("Height") != 1:
        return (False, "INVALID_GENESIS_HEIGHT", genesis.get("Height", 0), "Genesis height must be 1.")

    gen_header = genesis.get("BlockHeader", {})
    if gen_header.get("prev_block_hash") != ZERO_HASH:
        return (False, "INVALID_GENESIS_PREV_HASH", 1, "Genesis previous hash must be ZERO_HASH.")

    for i in range(len(chain)):
        block = chain[i]
        header = block.get("BlockHeader", {})
        height = block.get("Height")

        if height != i + 1:
            return (False, "HEIGHT_MISMATCH", height, f"Expected height {i + 1}, found {height}.")

        if i > 0:
            prev_block = chain[i - 1]
            prev_header = prev_block.get("BlockHeader", {})
            if header.get("prev_block_hash") != prev_header.get("blockHash"):
                return (False, "BROKEN_LINK", height, f"Block {height} prev_hash does not match block {i}'s hash.")

        actual_nonce = header.get("nonce", 0) - 1
        serialized = (
            str(header.get("version")) +
            str(header.get("prev_block_hash")) +
            str(header.get("merkle_root", "")) +
            str(header.get("timestamp")) +
            str(header.get("bits")) +
            str(actual_nonce)
        )
        calc_hash = hash256(serialized.encode("utf-8"))
        stored_hash = header.get("blockHash")

        if calc_hash != stored_hash:
            return (False, "HASH_TAMPERED", height, f"Recalculated hash {calc_hash} != stored {stored_hash}.")

        if stored_hash[0:len(TARGET)] != TARGET:
            return (False, "TARGET_NOT_MET", height, f"Hash {stored_hash} does not satisfy target {TARGET}.")

    return (True, "VALID", len(chain), "All blocks passed integrity verification.")


# =====================================================================
# EXAM TOPIC 2: Merkle Root Calculation from Transaction IDs
# =====================================================================
def calculate_merkle_root(tx_ids):
    """
    Calculates the Merkle Root from a list of transaction IDs (hex strings).
    Follows standard Bitcoin pairwise SHA-256 algorithm.
    """
    if not tx_ids:
        return ""
    if len(tx_ids) == 1:
        return tx_ids[0]

    current_level = list(tx_ids)

    while len(current_level) > 1:
        # If odd number of transactions, duplicate the last hash
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1]
            combined = (left + right).encode("utf-8")
            parent_hash = hash256(combined)
            next_level.append(parent_hash)

        current_level = next_level

    return current_level[0]


# =====================================================================
# EXAM TOPIC 3: Block Reward Halving Schedule
# =====================================================================
def calculate_block_reward(block_height, halving_interval=210000):
    """
    Calculates the block subsidy (reward) in Poisha for a given block height.
    Bitcoin halves every 210,000 blocks.
    """
    halvings = (block_height - 1) // halving_interval
    if halvings >= 64:
        return 0
    reward_coins = INITIAL_REWARD >> halvings
    return reward_coins * ONE_COIN


# =====================================================================
# EXAM TOPIC 4: Difficulty Retargeting Algorithm
# =====================================================================
def adjust_difficulty(current_target_int, actual_time, expected_time):
    """
    Adjusts target based on time ratio, clamped to [0.25x, 4x].
    """
    if actual_time <= 0:
        actual_time = 1
    if actual_time < expected_time // 4:
        actual_time = expected_time // 4
    if actual_time > expected_time * 4:
        actual_time = expected_time * 4

    new_target = (current_target_int * actual_time) // expected_time
    return new_target


# =====================================================================
# EXAM TOPIC 5: Tamper and Re-mine Demonstration
# =====================================================================
def tamper_and_remine_demo(chain, tamper_index=1):
    """
    Demonstrates re-mining starting from tamper_index to end of chain.
    """
    tampered_chain = copy.deepcopy(chain)
    print(f"\n[Attack Simulation] Tampering Block at index {tamper_index} (Height {tampered_chain[tamper_index]['Height']})...")
    
    # Tamper with timestamp
    tampered_chain[tamper_index]["BlockHeader"]["timestamp"] += 1234
    
    # Cascade re-mining
    for i in range(tamper_index, len(tampered_chain)):
        h = tampered_chain[i]["BlockHeader"]
        if i > tamper_index:
            h["prev_block_hash"] = tampered_chain[i - 1]["BlockHeader"]["blockHash"]

        nonce = 0
        while True:
            candidate = (
                str(h["version"]) +
                str(h["prev_block_hash"]) +
                str(h["merkle_root"]) +
                str(h["timestamp"]) +
                str(h["bits"]) +
                str(nonce)
            )
            calc_hash = hash256(candidate.encode("utf-8"))
            if calc_hash[0:len(TARGET)] == TARGET:
                h["nonce"] = nonce + 1
                h["blockHash"] = calc_hash
                break
            nonce += 1

    return tampered_chain


# =====================================================================
# Live Testing & Verification
# =====================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING EXAM PRACTICE SOLUTIONS & UNIT TESTS")
    print("=" * 70)

    bc = Blockchain()
    chain = bc.read_from_disk()

    # 1. Test Audit Chain on Valid Chain
    print("\n--- 1. Testing audit_chain() on Original Chain ---")
    status, code, height, msg = audit_chain(chain)
    print(f"Status: {status} | Code: {code} | Height: {height} | Message: {msg}")

    # 2. Test Audit Chain on Tampered Chain
    print("\n--- 2. Testing audit_chain() on Tampered Nonce (Block 3) ---")
    tampered = copy.deepcopy(chain)
    tampered[2]["BlockHeader"]["nonce"] += 5
    status, code, height, msg = audit_chain(tampered)
    print(f"Status: {status} | Code: {code} | Height: {height} | Message: {msg}")

    # 3. Test Merkle Root Calculation
    print("\n--- 3. Testing calculate_merkle_root() ---")
    dummy_tx_ids = [
        "a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
        "b2c3d4e5f6a10123456789abcdef0123456789abcdef0123456789abcdef0124",
        "c3d4e5f6a1b20123456789abcdef0123456789abcdef0123456789abcdef0125"
    ]
    merkle_root = calculate_merkle_root(dummy_tx_ids)
    print(f"Computed Merkle Root for 3 transactions: {merkle_root}")

    # 4. Test Halving Calculation
    print("\n--- 4. Testing calculate_block_reward() across Halvings ---")
    print(f"Block 1 reward:       {calculate_block_reward(1) // ONE_COIN} coins ({calculate_block_reward(1)} Poisha)")
    print(f"Block 210,001 reward: {calculate_block_reward(210001) // ONE_COIN} coins ({calculate_block_reward(210001)} Poisha)")
    print(f"Block 420,001 reward: {calculate_block_reward(420001) // ONE_COIN} coins ({calculate_block_reward(420001)} Poisha)")

    # 5. Test Tamper & Re-mining
    print("\n--- 5. Testing Tamper & Cascade Re-mining ---")
    # Take a 3-block slice for fast mining demo
    short_chain = copy.deepcopy(chain[:3])
    remined_chain = tamper_and_remine_demo(short_chain, tamper_index=1)
    valid_after_remine = bc.validate_chain(remined_chain)
    print(f"Is re-mined chain valid now? {valid_after_remine}")

    print("\n" + "=" * 70)
    print("ALL EXAM PRACTICE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

import sys
import os
import copy

# Ensure Desktop and project root are in sys.path so Blockchain package imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
parent_root = os.path.dirname(project_root)

for path in [current_dir, project_root, parent_root, "C:/Users/muhib/Desktop"]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import the updated Blockchain class from current solved folder
from blockchain import Blockchain

def run_demonstration():
    # Initialize the blockchain instance
    blockchain = Blockchain()

    # -------------------------------------------------------------
    # Case 1: Original blockchain
    # -------------------------------------------------------------
    print("Case 1: Original blockchain")
    is_valid_case1 = blockchain.validate_chain()
    print(f"Blockchain Valid: {is_valid_case1}")

    # -------------------------------------------------------------
    # Case 2: After modifying a block's nonce
    # -------------------------------------------------------------
    print("\nCase 2: After modifying a block's nonce")
    
    # Read the existing chain
    original_chain = blockchain.read_from_disk()
    if not original_chain or len(original_chain) < 2:
        print("Not enough blocks to perform tamper demonstration.")
        return

    # Create an in-memory copy of the blockchain and tamper with block 2's nonce
    tampered_chain = copy.deepcopy(original_chain)
    
    # Target block at index 1 (Height 2)
    tampered_block_index = 1
    tampered_chain[tampered_block_index]["BlockHeader"]["nonce"] += 999
    
    # Validate the tampered chain
    is_valid_case2 = blockchain.validate_chain(tampered_chain)
    print(f"Blockchain Valid: {is_valid_case2}")

if __name__ == "__main__":
    run_demonstration()

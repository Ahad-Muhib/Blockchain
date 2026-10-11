# High-Yield Exam Preparation: Blockchain Concepts, Coding Questions & Detailed Answers

This guide is designed for your blockchain exam. It includes high-probability coding questions, step-by-step solutions, line-by-line explanations, and essential theoretical / viva questions.

---

## Question 1: Advanced Integrity Verification with Fault Localization

### Problem Statement
In the lab, `validate_chain()` simply returned `True` or `False`. An exam question may ask:
> "Write a method `audit_chain(chain)` that verifies blockchain integrity and returns a detailed status tuple: `(is_valid: bool, error_code: str, failed_height: int, details: str)`. If invalid, pinpoint the exact block and the specific rule that was violated."

### Code Solution
```python
from Blockchain.config import TARGET, ZERO_HASH
from Blockchain.Backend.Util.util import hash256

def audit_chain(chain):
    """
    Audits the blockchain and localizes the exact fault if invalid.
    Returns:
        (is_valid, error_code, failed_height, details)
    """
    # Rule 1: Check if empty
    if not chain or len(chain) == 0:
        return (False, "EMPTY_CHAIN", 0, "The blockchain contains no blocks.")

    # Rule 2: Verify Genesis Block
    genesis = chain[0]
    if genesis.get("Height") != 1:
        return (False, "INVALID_GENESIS_HEIGHT", genesis.get("Height", 0), "Genesis height must be 1.")

    gen_header = genesis.get("BlockHeader", {})
    if gen_header.get("prev_block_hash") != ZERO_HASH:
        return (False, "INVALID_GENESIS_PREV_HASH", 1, "Genesis previous hash must be ZERO_HASH.")

    # Rule 3, 4, 5: Verify all blocks
    for i in range(len(chain)):
        block = chain[i]
        header = block.get("BlockHeader", {})
        height = block.get("Height")

        # Check sequence
        if height != i + 1:
            return (False, "HEIGHT_MISMATCH", height, f"Expected height {i + 1}, found {height}.")

        # Check parent pointer
        if i > 0:
            prev_block = chain[i - 1]
            prev_header = prev_block.get("BlockHeader", {})
            if header.get("prev_block_hash") != prev_header.get("blockHash"):
                return (False, "BROKEN_LINK", height, f"Previous hash does not match block {i}'s hash.")

        # Recalculate hash (accounting for post-hash nonce increment)
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

        # Check target
        if stored_hash[0:len(TARGET)] != TARGET:
            return (False, "TARGET_NOT_MET", height, f"Hash {stored_hash} does not satisfy target {TARGET}.")

    return (True, "VALID", len(chain), "All blocks passed integrity verification.")
```

### Line-by-Line Explanation
1. `if not chain or len(chain) == 0:`: Immediately catches missing data and returns error code `EMPTY_CHAIN`.
2. `if genesis.get("Height") != 1:`: Ensures nobody deleted the genesis block or prepended unauthorized blocks.
3. `gen_header.get("prev_block_hash") != ZERO_HASH`: Checks that genesis is rooted at `ZERO_HASH`.
4. `if height != i + 1:`: Detects skipped blocks (e.g., block 3 followed directly by block 5).
5. `header.get("prev_block_hash") != prev_header.get("blockHash")`: Ensures tamper-proof chain continuity.
6. `actual_nonce = header.get("nonce", 0) - 1`: Accurately handles the codebase's post-hash nonce increment.
7. `calc_hash != stored_hash`: Detects if any header data (transactions, timestamp, nonce, bits) was changed.
8. `stored_hash[0:len(TARGET)] != TARGET`: Guarantees proof-of-work was fulfilled.

---

## Question 2: Merkle Root Calculation from Block Transactions

### Problem Statement
In `blockchain.py`, notice that `merkle_root = ''` is currently a placeholder.
> "Write a function `calculate_merkle_root(tx_ids)` that takes a list of transaction ID strings (hex) and computes the Merkle Root using SHA-256. If there is an odd number of hashes at any level, duplicate the last hash before pairing."

### Code Solution
```python
from Blockchain.Backend.Util.util import hash256

def calculate_merkle_root(tx_ids):
    """
    Computes the Merkle Root from a list of transaction IDs (hex strings).
    Follows standard Bitcoin Merkle Tree algorithm.
    """
    if not tx_ids:
        return ""

    # Base case: if only one transaction, its hash is the Merkle root
    if len(tx_ids) == 1:
        return tx_ids[0]

    current_level = list(tx_ids)

    # Continue combining levels until only one root hash remains
    while len(current_level) > 1:
        # If odd number of hashes, duplicate the last hash
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        next_level = []
        # Pair adjacent hashes: (0,1), (2,3), etc.
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1]
            combined = (left + right).encode("utf-8")
            parent_hash = hash256(combined)
            next_level.append(parent_hash)

        current_level = next_level

    return current_level[0]
```

### Detailed Explanation
- **Why a Merkle Tree?**: A block can contain thousands of transactions. Instead of hashing all transactions together into one giant string, a Merkle Tree hashes pairs hierarchically into a single 32-byte root.
- **Why duplicate the last item?**: Trees require pairs (2 children per node). If a block has 3 transactions $[T_1, T_2, T_3]$, it duplicates $T_3$ into $[T_1, T_2, T_3, T_3]$ so it can form pairs $(T_1, T_2)$ and $(T_3, T_3)$.
- **SPV (Simple Payment Verification) Advantage**: A light node only needs the 80-byte block header and a logarithmic path (Merkle Proof) to verify that a transaction is included, without downloading the entire blockchain!

---

## Question 3: Dynamic Difficulty Adjustment (Retargeting)

### Problem Statement
> "In Bitcoin, mining difficulty adjusts every 2016 blocks so that each block takes approximately 10 minutes (600 seconds). Implement `adjust_difficulty(current_bits, actual_time_taken, expected_time_taken)` to calculate the new difficulty target. Explain the purpose of difficulty adjustment."

### Code Solution
```python
def adjust_difficulty(current_target_int, actual_time, expected_time):
    """
    Adjusts mining difficulty target based on time taken vs expected time.
    new_target = current_target * (actual_time / expected_time)
    Clamped to a maximum factor of 4 to prevent wild swings.
    """
    # Prevent division by zero
    if actual_time <= 0:
        actual_time = 1

    # Clamp actual time to between 1/4 and 4x of expected time
    if actual_time < expected_time // 4:
        actual_time = expected_time // 4
    if actual_time > expected_time * 4:
        actual_time = expected_time * 4

    new_target_int = (current_target_int * actual_time) // expected_time

    # Ensure target does not exceed max target (lowest difficulty)
    max_target = (1 << 224) - 1  # Example max target
    if new_target_int > max_target:
        new_target_int = max_target

    return new_target_int
```

### Detailed Explanation
- **If blocks were mined too fast** (`actual_time < expected_time`): More miners joined or hash power increased. The ratio is $< 1$, so `new_target` becomes smaller $\rightarrow$ harder to find $\rightarrow$ slows down block generation.
- **If blocks were mined too slow** (`actual_time > expected_time`): Miners left. The ratio is $> 1$, so `new_target` becomes larger $\rightarrow$ easier to find $\rightarrow$ speeds up block generation.
- **The $4\times$ clamp**: Bitcoin enforces a rule that difficulty can change by at most a factor of 4 in either direction during a single retargeting window, protecting against manipulation or sudden network instability.

---

## Question 4: Block Reward Halving Calculation & Coinbase Validation

### Problem Statement
In `config.py`:
`INITIAL_REWARD = 50`, `ONE_COIN = 100_000_000` (Poisha / Satoshis), halving every 210,000 blocks.
> "Write a function `calculate_block_reward(height)` and a validation function `validate_coinbase_tx(coinbase_tx, block_height)` to ensure that the miner did not claim more reward than legally allowed for that block height."

### Code Solution
```python
from Blockchain.config import INITIAL_REWARD, ONE_COIN

def calculate_block_reward(block_height, halving_interval=210000):
    """
    Calculates the exact block subsidy in Poisha for a given block height.
    Halves every 210,000 blocks. After 64 halvings, reward is 0.
    """
    # Number of halvings that have occurred
    halvings = (block_height - 1) // halving_interval

    if halvings >= 64:
        return 0

    reward_coins = INITIAL_REWARD >> halvings  # Bitwise right shift divides by 2**halvings
    reward_poisha = reward_coins * ONE_COIN
    return reward_poisha

def validate_coinbase_tx(coinbase_tx, block_height):
    """
    Verifies that the coinbase transaction:
    1. Has exactly 1 input with prev_index = 0xFFFFFFFF.
    2. Does not output more coins than allowed by the halving schedule.
    """
    expected_subsidy = calculate_block_reward(block_height)
    
    total_output = 0
    for tx_out in coinbase_tx.tx_outs:
        total_output += tx_out.amount

    if total_output > expected_subsidy:
        return False, f"Coinbase overpayment! Claimed {total_output}, allowed {expected_subsidy}"

    return True, "Coinbase valid."
```

### Detailed Explanation
- **`>> halvings`**: In binary, shifting right by 1 bit (`>> 1`) divides an integer by 2.
- **Halving Mechanism**: Satoshi Nakamoto designed halving to create controlled digital scarcity (deflationary currency). There will only ever be 21 million Bitcoins created.
- **Validation Importance**: If a malicious miner modifies their software to mint 1,000 coins instead of 50, other nodes running `validate_coinbase_tx` reject the block immediately.

---

## Question 5: Re-mining Attack (Why Changing Old Blocks is Computationally Infeasible)

### Problem Statement
> "Suppose an attacker modifies a transaction in Block 2 of a 7-block blockchain.
> 1. What happens if the attacker only recalculates Block 2's hash?
> 2. What must the attacker do to make the whole blockchain valid again?
> 3. Write a Python function `tamper_and_remine(chain, block_index, new_nonce, target)` demonstrating this cascade effect."

### Code Solution
```python
import copy
from Blockchain.Backend.Util.util import hash256

def tamper_and_remine(chain, tamper_index, new_nonce_start, target):
    """
    Demonstrates the cascade effect of tampering:
    When block k is altered, block k and ALL subsequent blocks (k+1, k+2, ...)
    must be re-mined because their prev_block_hash pointers broke!
    """
    tampered_chain = copy.deepcopy(chain)

    print(f"--- Attacker tampers with Block {tampered_chain[tamper_index]['Height']} ---")
    
    # Cascade re-mining from tamper_index to end of chain
    for i in range(tamper_index, len(tampered_chain)):
        header = tampered_chain[i]["BlockHeader"]

        # If after tamper_index, update prev_block_hash to point to the newly mined previous block
        if i > tamper_index:
            header["prev_block_hash"] = tampered_chain[i - 1]["BlockHeader"]["blockHash"]

        # Re-mine this block
        nonce = 0
        while True:
            candidate_string = (
                str(header["version"]) +
                str(header["prev_block_hash"]) +
                str(header["merkle_root"]) +
                str(header["timestamp"]) +
                str(header["bits"]) +
                str(nonce)
            )
            h = hash256(candidate_string.encode("utf-8"))
            if h[0:len(target)] == target:
                header["nonce"] = nonce + 1  # Maintain the +1 convention of this repo
                header["blockHash"] = h
                print(f"Re-mined Block {tampered_chain[i]['Height']}: Nonce {header['nonce']}, Hash {h}")
                break
            nonce += 1

    return tampered_chain
```

### Detailed Explanation
- If the attacker only alters Block 2 and re-mines Block 2, Block 3's stored `prev_block_hash` still points to the *old* Block 2 hash! Block 3 is now invalid.
- To fix Block 3, its `prev_block_hash` must be updated to the new Block 2 hash. But changing Block 3's header breaks Block 3's Proof-of-Work! So Block 3 must be re-mined.
- This cascades all the way to the tip of the chain.
- In a real decentralized network, the honest network continues mining blocks while the attacker tries to catch up. Unless the attacker controls $> 50\%$ of the entire world's mining power (51% attack), they can never outpace the honest chain!

---

## Question 6: High-Yield Viva & Theory Questions for Tomorrow's Exam

### Q1: Why is SHA-256 considered secure for blockchain?
**Answer**:
1. **Pre-image resistance (One-way)**: Given a hash $H$, it is computationally impossible to find the input $x$ such that $\text{SHA256}(x) = H$.
2. **Second pre-image resistance**: Given $x$, it is impossible to find a different $y$ such that $\text{SHA256}(x) = \text{SHA256}(y)$.
3. **Collision resistance**: It is impossible to find *any* two different inputs that produce the same hash.
4. **Avalanche Effect**: Changing even a single bit in the input produces a completely unrecognizable, drastically different output.

---

### Q2: Why does the blockchain hash the Block Header instead of the entire Block Body?
**Answer**:
1. **Efficiency**: The block header is fixed-size (e.g. 80 bytes in Bitcoin). Hashing 80 bytes repeatedly in a mining loop is orders of magnitude faster than hashing megabytes of transaction data every iteration.
2. **Merkle Root summary**: The block header already includes the `merkle_root`. Because the Merkle root is a cryptographic summary of all transactions, any change to any transaction automatically changes the Merkle root, which invalidates the block header. Thus, hashing the header is 100% equivalent to securing the entire block!
3. **Light Nodes (SPV)**: Mobile wallets and light nodes only need to download block headers to verify chain proof-of-work.

---

### Q3: What is the role of the Nonce in Proof of Work?
**Answer**:
- "Nonce" stands for **Number used ONCE**.
- In the block header, fields like version, previous hash, Merkle root, and target are fixed.
- Because a cryptographic hash function is deterministic, hashing the same header produces the same hash every time.
- The nonce is an arbitrary counter field that the miner can change on every attempt. By varying the nonce ($0, 1, 2, 3, \dots$), the miner generates completely new pseudo-random hashes until one happens to be below the target.

---

### Q4: Why is the first block called Genesis Block, and what makes it special?
**Answer**:
- The Genesis block is Block 1 (or Block 0 in Bitcoin).
- It is hardcoded into the software.
- It has no previous block, so its `prev_block_hash` is conventionally set to `ZERO_HASH` (64 zeros).
- Its coinbase reward cannot be spent in Bitcoin (by Satoshi's convention).

---

### Q5: What is the "Longest Chain Rule" (Nakamoto Consensus)?
**Answer**:
- When two miners produce valid blocks at the same time, a temporary fork occurs.
- Nodes will follow the branch with the greatest cumulative Proof of Work (commonly known as the longest valid chain).
- As soon as the next block is mined on one branch, that branch becomes longer, and all nodes re-organize to adopt it, discarding the shorter branch as "orphaned blocks".

---

### Q6: In our lab code, why did `stored_nonce - 1` have to be used during validation?
**Answer**:
- In `BlockHeader.mine()`:
  ```python
  self.blockHash = hash256(...)
  self.nonce += 1
  ```
  The code computed the hash first with the current nonce, and then immediately incremented `self.nonce` by 1 before checking the while loop condition.
- When a valid hash was found, `self.nonce` had already been incremented.
- Thus, the nonce stored in the block object on disk was $1$ higher than the value that actually generated the matching hash.
- During validation, recalculating with `stored_nonce - 1` reproduces the exact original string that created `blockHash`.

# Lab Task Solution: Blockchain Integrity Verification

## Overview of the Lab Task

The objective is to implement a verification method named `validate_chain()` in the `Blockchain` class to verify whether the entire blockchain stored on disk (or in memory) maintains its cryptographic and structural integrity.

### 5 Core Requirements:
1. **Empty Chain Check**: Return `False` if the blockchain is empty or missing.
2. **Genesis Block Check**: Ensure block 1 has `Height == 1` and uses `ZERO_HASH` (64 zeros) as its `prev_block_hash`.
3. **Chain Continuity Check**: Ensure each consecutive block has sequential height (`Height == i + 1`) and points to the previous block's hash (`prev_block_hash == prev_block.blockHash`).
4. **Hash Recalculation Check**: Re-hash the block header using the block's metadata and verify that the calculated hash equals the stored `blockHash`.
   - **Crucial nuance**: The mining code in `blockheader.py` increments `self.nonce += 1` *after* calculating the hash. Thus, the nonce stored in the block header is $1$ greater than the nonce that satisfied the target. We must use `(stored_nonce - 1)` when recalculating!
5. **Mining Target Check**: Check that each block's hash satisfies the Proof of Work difficulty target (`TARGET = "0000"`).

If **all** checks pass for **all** blocks, return `True`. If any check fails at any point, immediately return `False`.

---

## Complete Solution Code (`validate_chain`)

```python
def validate_chain(self, chain=None):
    """
    Validates the integrity of the blockchain according to the lab requirements.
    
    Parameters:
        chain (list, optional): Blockchain list to validate. If None, reads from disk.
        
    Returns:
        bool: True if the chain is completely valid, False otherwise.
    """
    # Step 1: Read chain from disk if not provided
    if chain is None:
        chain = self.read_from_disk()

    # Requirement 1: Return False if the blockchain is empty or database does not exist
    if not chain or len(chain) == 0:
        return False

    # Requirement 2: Check that the first block (Genesis) has height 1 and uses ZERO_HASH
    genesis_block = chain[0]
    if genesis_block.get("Height") != 1:
        return False

    genesis_header = genesis_block.get("BlockHeader", {})
    if genesis_header.get("prev_block_hash") != ZERO_HASH:
        return False

    # Requirement 3, 4, 5: Verify all blocks in the chain
    for i in range(len(chain)):
        current_block = chain[i]
        current_header = current_block.get("BlockHeader", {})

        # Requirement 3a: Verify correct height sequence
        expected_height = i + 1
        if current_block.get("Height") != expected_height:
            return False

        # Requirement 3b: Verify previous-block hash linkage for all blocks after Genesis
        if i > 0:
            prev_block = chain[i - 1]
            prev_header = prev_block.get("BlockHeader", {})
            if current_header.get("prev_block_hash") != prev_header.get("blockHash"):
                return False

        # Requirement 4: Recalculate each block's hash and compare with the stored hash
        # NOTE: BlockHeader.mine() increments the nonce after computing the hash:
        #   self.blockHash = hash256(...)
        #   self.nonce += 1
        # Hence, the valid hash was generated using (stored_nonce - 1).
        stored_nonce = current_header.get("nonce", 0)
        actual_nonce = stored_nonce - 1

        version = current_header.get("version")
        prev_block_hash = current_header.get("prev_block_hash")
        merkle_root = current_header.get("merkle_root", "")
        timestamp = current_header.get("timestamp")
        bits = current_header.get("bits")

        # Reconstruct the exact serialized string format used during mining
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

        # Compare recalculated hash with the stored hash
        if recalculated_hash != stored_hash:
            return False

        # Requirement 5: Check that the block hash satisfies the mining target
        if stored_hash[0:len(TARGET)] != TARGET:
            return False

    # All checks passed for every block in the blockchain
    return True
```

---

## Detailed Line-by-Line Code Explanation

Let's dissect each line of code so you understand exactly what it does and why it was written this way:

### 1. Function Definition & Parameter Handling
```python
def validate_chain(self, chain=None):
```
- **What it does**: Defines the method `validate_chain` inside the `Blockchain` class.
- **Why `chain=None`?**: When called without arguments (`blockchain.validate_chain()`), it defaults to checking the live chain saved on disk. When testing tampered blocks (Case 2), we can pass an in-memory modified chain list without corrupting the original database file.

```python
if chain is None:
    chain = self.read_from_disk()
```
- **What it does**: If no chain was passed, calls `self.read_from_disk()`, which reads the JSON list of blocks from `Data/uapcoin-blockchain`.

---

### 2. Requirement 1: Empty Chain Verification
```python
if not chain or len(chain) == 0:
    return False
```
- **What it does**: Checks if `chain` is `False`, `None`, or an empty list `[]`.
- **Why**: In `database.py`, `read()` returns `False` if the database file doesn't exist, and `[]` if the file is blank. A blockchain must contain at least the Genesis block to be valid. If there are no blocks, it returns `False`.

---

### 3. Requirement 2: Genesis Block Verification
```python
genesis_block = chain[0]
if genesis_block.get("Height") != 1:
    return False
```
- **What it does**: Accesses the first element `chain[0]` (the Genesis block). It checks whether its `"Height"` attribute equals 1.
- **Why**: In this implementation, the Genesis block is initialized with height 1 (`self.add_block(1, ZERO_HASH)` in `blockchain.py`). If the first block has any height other than 1, someone may have sliced or corrupted the chain history.

```python
genesis_header = genesis_block.get("BlockHeader", {})
if genesis_header.get("prev_block_hash") != ZERO_HASH:
    return False
```
- **What it does**: Extracts the `"BlockHeader"` dictionary from the Genesis block and verifies that `"prev_block_hash"` equals `ZERO_HASH` (64 zeros: `"0" * 64`).
- **Why**: The Genesis block is the very first block in existence. Since no block preceded it, its previous block hash must be the well-known constant `ZERO_HASH`.

---

### 4. Iterating Through Every Block
```python
for i in range(len(chain)):
    current_block = chain[i]
    current_header = current_block.get("BlockHeader", {})
```
- **What it does**: A `for` loop that iterates over every block by index $i$ from $0$ up to $N-1$.
- **Why**: We must verify every single block from Genesis to the latest block. If even one block is tampered with, the entire chain is compromised.

---

### 5. Requirement 3: Height & Previous Hash Continuity
```python
expected_height = i + 1
if current_block.get("Height") != expected_height:
    return False
```
- **What it does**: At index $0$, height must be $1$; at index $1$, height must be $2$; and at index $i$, height must be $i + 1$.
- **Why**: Ensures there are no skipped blocks, duplicate heights, or missing blocks in the sequence.

```python
if i > 0:
    prev_block = chain[i - 1]
    prev_header = prev_block.get("BlockHeader", {})
    if current_header.get("prev_block_hash") != prev_header.get("blockHash"):
        return False
```
- **What it does**: For every block after the Genesis block ($i > 0$), it retrieves the previous block (`chain[i - 1]`) and compares its stored `blockHash` with the current block's `prev_block_hash`.
- **Why**: This is the core "chain" mechanism of blockchain! Each block cryptographically points to the hash of the parent block. If an attacker modifies block $k$, the hash of block $k$ changes, causing block $k+1$'s `prev_block_hash` to mismatch and breaking the chain.

---

### 6. Requirement 4: Hash Recalculation & The Nonce Increment Quirk
```python
stored_nonce = current_header.get("nonce", 0)
actual_nonce = stored_nonce - 1
```
- **What it does**: Retrieves the integer `nonce` stored in the block header and subtracts 1 to find `actual_nonce`.
- **Why is `- 1` required?**: Look at `Backend/Core/blockheader.py` line 12–16:
  ```python
  def mine(self, target):
      while (self.blockHash[0:len(target)] != target):
          self.blockHash = hash256(
              (str(self.version) + self.prev_block_hash + self.merkle_root + str(self.timestamp) + str(self.bits) + str(self.nonce)).encode('utf-8'))
          self.nonce += 1
  ```
  Notice the order of operations in the while loop:
  1. `hash256(...)` is calculated using `self.nonce`.
  2. `self.nonce += 1` increments `self.nonce` immediately after hashing!
  3. The `while` condition checks if `self.blockHash` satisfies the target.
  4. When the loop finds a winning hash, `self.nonce` has already been incremented by 1!
  5. Therefore, the saved `nonce` stored on disk is $1$ greater than the nonce that produced the hash.
  6. Hence, when recalculating the block's hash, we must use `actual_nonce = stored_nonce - 1`.

```python
version = current_header.get("version")
prev_block_hash = current_header.get("prev_block_hash")
merkle_root = current_header.get("merkle_root", "")
timestamp = current_header.get("timestamp")
bits = current_header.get("bits")

serialized_header = (
    str(version) +
    str(prev_block_hash) +
    str(merkle_root) +
    str(timestamp) +
    str(bits) +
    str(actual_nonce)
)
```
- **What it does**: Extracts all block header fields and concatenates them in the exact same order as `BlockHeader.mine()`:
  `str(version) + prev_block_hash + merkle_root + str(timestamp) + str(bits) + str(actual_nonce)`
- **Why**: Cryptographic hashing (SHA-256) is sensitive to even a single character difference (the Avalanche Effect). The string must match the exact data that was hashed during mining.

```python
recalculated_hash = hash256(serialized_header.encode('utf-8'))
stored_hash = current_header.get("blockHash")

if recalculated_hash != stored_hash:
    return False
```
- **What it does**: Encodes the concatenated string into UTF-8 bytes, computes the SHA-256 hash using `hash256()`, and compares it to the block's stored `blockHash`.
- **Why**: If an attacker tampers with any field (e.g., changes transactions, modifies timestamp, changes nonce, or edits the stored hash), `recalculated_hash` will NOT match `stored_hash`, immediately detecting the fraud!

---

### 7. Requirement 5: Mining Target (Proof of Work) Verification
```python
if stored_hash[0:len(TARGET)] != TARGET:
    return False
```
- **What it does**: Checks if the first characters of `stored_hash` match `TARGET` (e.g., `"0000"`).
- **Why**: Proof of Work requires the hash of a valid block to be smaller than the network target (in this simplified implementation, having a prefix of four zeros `"0000"`). If a block's hash does not satisfy the difficulty requirement, it is not a valid Proof of Work, so return `False`.

---

### 8. Final Return
```python
return True
```
- **What it does**: If all iterations of the loop complete without any check failing, the entire blockchain is verified and valid. Returns `True`.

---

## Demonstration Test Cases Walkthrough

The script `demo_validation.py` demonstrates both required test cases:

### Case 1: Original Blockchain
```python
print("Case 1: Original blockchain")
is_valid_case1 = blockchain.validate_chain()
print(f"Blockchain Valid: {is_valid_case1}")
```
- **Execution**: Validates the 7 blocks currently in `Data/uapcoin-blockchain`.
- **Result**:
  ```
  Case 1: Original blockchain
  Blockchain Valid: True
  ```

### Case 2: After Modifying a Block's Nonce
```python
print("\nCase 2: After modifying a block's nonce")
tampered_chain = copy.deepcopy(original_chain)
tampered_chain[1]["BlockHeader"]["nonce"] += 999
is_valid_case2 = blockchain.validate_chain(tampered_chain)
print(f"Blockchain Valid: {is_valid_case2}")
```
- **Execution**:
  1. Clones the chain into `tampered_chain`.
  2. Modifies block 2's nonce by adding 999.
  3. Calls `validate_chain(tampered_chain)`.
  4. When block 2 is validated, `recalculated_hash` uses the altered nonce, resulting in a completely different SHA-256 hash that does not match `stored_hash`.
  5. `validate_chain()` immediately returns `False`.
- **Result**:
  ```
  Case 2: After modifying a block's nonce
  Blockchain Valid: False
  ```

---

## How to Run the Demonstration

Run the following command from PowerShell or Command Prompt:

```bash
python "solved questions/demo_validation.py"
```

### Exact Terminal Output:
```
Case 1: Original blockchain
Blockchain Valid: True

Case 2: After modifying a block's nonce
Blockchain Valid: False
```

Take a screenshot of this output for your lab submission!

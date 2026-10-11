# Blockchain Complete Reference & Possible Exam Questions with Answers

This document contains:
1. **Part 1: Exhaustive Reference of the Entire Codebase** — Explaining every single class, function, parameter, and method across every file in the project, complete with practical code snippets showing how to use each one.
2. **Part 2: High-Probability Exam Questions with Detailed Answers** — Coding and theoretical exam questions that can be asked on this codebase tomorrow, with step-by-step solutions and explanations.

---

# PART 1: COMPLETE CODEBASE REFERENCE (EVERY CLASS & FUNCTION EXPLAINED)

---

## 1. Global Configuration (`config.py`)

### Purpose
Contains all global constants and network parameters used across the blockchain system.

### Constants & Variables
- `VERSION = 1.0`: Current protocol/software version encoded into block headers.
- `TARGET = "0000"`: Mining difficulty target string. Any valid block hash must start with this prefix (Proof-of-Work threshold).
- `COIN_NAME = "UAP Coin"`: Name of the native cryptocurrency.
- `ZERO_HASH = "0" * 64`: A 64-character hex string representing the null/genesis hash. Used as `prev_block_hash` for the Genesis block.
- `ZERO_HASH_BYTES = bytes.fromhex(ZERO_HASH)`: 32 raw null bytes (`b'\x00'*32`). Used in transaction inputs for Coinbase transactions.
- `INITIAL_REWARD = 50`: Initial mining subsidy awarded per mined block (50 UAP Coins).
- `CURRENT_REWARD = INITIAL_REWARD`: Current active mining reward.
- `ONE_COIN = 100_000_000`: Denomination factor. 1 UAP Coin = 100,000,000 Poisha (equivalent to Satoshis in Bitcoin).

### Practical Usage Example
```python
from Blockchain.config import TARGET, ZERO_HASH, ONE_COIN, CURRENT_REWARD

# Convert 5 UAP coins into smallest unit (Poisha)
poisha = 5 * ONE_COIN  # 500,000,000 Poisha

# Check if a hash satisfies proof of work
is_mined = block_hash.startswith(TARGET)
```

---

## 2. Utility Module (`Backend/Util/util.py`)

### Purpose
Provides cryptographic hashing, Base58 encoding/decoding, endianness conversions, and variable-length integer serialization (Varint) following the Bitcoin standard.

---

### Functions

#### `hash256(data)` & `hash256_bytes(data)`
- **`hash256(data)`**: Takes `bytes` or utf-8 encoded string and returns the SHA-256 hash as a **hexadecimal string** (64 characters).
- **`hash256_bytes(data)`**: Takes `bytes` and returns the raw 32-byte hash digest.
```python
from Blockchain.Backend.Util.util import hash256, hash256_bytes

text_bytes = "Blockchain Data".encode("utf-8")
hex_hash = hash256(text_bytes)        # '5b281b...'
raw_bytes = hash256_bytes(text_bytes)  # b'\x5b\x28...'
```

#### `hash160(s)` & `hash160_bytes(s)`
- **What it does**: Computes RIPEMD-160(SHA-256(`s`)). This double-hash produces a 20-byte digest.
- **Why it is used**: In Bitcoin and UAP Coin, public keys (33 or 65 bytes) are hashed with Hash160 to produce a compact 20-byte Public Key Hash (wallet address identifier).
```python
from Blockchain.Backend.Util.util import hash160, hash160_bytes

pubkey_bytes = bytes.fromhex("0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")
pkh_hex = hash160(pubkey_bytes)        # 40-character hex string
pkh_bytes = hash160_bytes(pubkey_bytes) # 20 raw bytes
```

#### `encode_base58(s)` & `decode_base58(s)`
- **`encode_base58(s)`**: Encodes raw bytes `s` into human-readable Base58 alphanumeric string (omits `0, O, I, l` to avoid visual confusion). Preserves leading zero bytes as `'1'`s.
- **`decode_base58(s)`**: Decodes a Base58Check address string back into 20-byte public key hash, verifying the 4-byte SHA-256 checksum at the end.
```python
from Blockchain.Backend.Util.util import encode_base58, decode_base58

address = "15EDkKeKEZRtMiASKZoncU2J8WLqjGk5Hz"
pubkey_hash = decode_base58(address)  # 20 bytes public key hash
```

#### `int_to_little_endian(n, length)` & `little_endian_to_int(b)`
- **`int_to_little_endian(n, length)`**: Converts an integer `n` into bytes of length `length` with the least significant byte first (little-endian, standard for Bitcoin protocol).
- **`little_endian_to_int(b)`**: Reconstructs an integer from little-endian bytes.
```python
from Blockchain.Backend.Util.util import int_to_little_endian, little_endian_to_int

b = int_to_little_endian(1, 4)   # b'\x01\x00\x00\x00'
n = little_endian_to_int(b)      # 1
```

#### `int_to_big_endian(n, length)` & `big_endian_to_int(b)`
- Standard big-endian conversions (network byte order).

#### `encode_varint(i)` & `read_varint(s)`
- **What is a Varint?**: A variable-length integer encoding used in Bitcoin to save space:
  - If $< 253$ (`0xfd`): 1 byte.
  - If $< 65,536$: prefix `0xfd` + 2 bytes little-endian.
  - If $< 4,294,967,296$: prefix `0xfe` + 4 bytes little-endian.
  - Otherwise: prefix `0xff` + 8 bytes little-endian.
```python
from Blockchain.Backend.Util.util import encode_varint
tx_count_bytes = encode_varint(3)  # b'\x03'
```

---

## 3. Database Layer (`Backend/Core/Database/database.py`)

### Purpose
Handles persistent JSON file storage for the blockchain ledger.

### Classes

#### `BaseDB`
- **Attributes**:
  - `self.basepath = "Data"`: Target folder.
  - `self.filepath`: Combined file path (e.g. `"Data/uapcoin-blockchain"`).
- **Methods**:
  - `BlockchainDBExists()`: Returns `True` if database file exists on disk, `False` otherwise.
  - `read()`: Opens file, reads JSON string, and deserializes into a Python list of block dicts. Returns `False` if file doesn't exist, `[]` if blank.
  - `update(data)`: Overwrites file with new JSON serialized data.
  - `write(item)`: Appends new item(s) to existing data and writes back to disk.

#### `BlockchainDB(BaseDB)`
- Subclasses `BaseDB` specifically for the blockchain database file (`self.filename = "uapcoin-blockchain"`).
- **Method `lastBlock()`**:
  - Reads data from disk and returns the last element `data[-1]` (the tip of the blockchain).

### Practical Usage Example
```python
from Blockchain.Backend.Core.Database.database import BlockchainDB

db = BlockchainDB()
if db.BlockchainDBExists():
    blocks = db.read()
    latest_block = db.lastBlock()
    print("Latest Block Height:", latest_block["Height"])
```

---

## 4. Block Header & Proof of Work (`Backend/Core/blockheader.py`)

### Purpose
Represents the 80-byte-style block header containing all metadata required for Proof-of-Work mining.

### Class: `BlockHeader`
- **Constructor `__init__(version, prev_block_hash, merkle_root, timestamp, bits, nonce=0)`**:
  - `version`: Protocol version (e.g. `1.0`).
  - `prev_block_hash`: Hash of parent block (64 hex characters).
  - `merkle_root`: Hash summarizing all transactions in this block.
  - `timestamp`: Unix epoch integer timestamp (`int(time.time())`).
  - `bits`: Target difficulty representation (`"ffff0000"`).
  - `nonce`: Integer counter altered to find valid Proof of Work.
  - `blockHash`: Resulting SHA-256 hash string satisfying the target.

- **Method `mine(target)`**:
  ```python
  def mine(self, target):
      while (self.blockHash[0:len(target)] != target):
          self.blockHash = hash256(
              (str(self.version) + self.prev_block_hash + self.merkle_root + 
               str(self.timestamp) + str(self.bits) + str(self.nonce)).encode('utf-8'))
          self.nonce += 1
  ```
  - Loops until `self.blockHash` starts with `target` (e.g. `"0000"`).
  - **Crucial Quirk**: Computes hash with `self.nonce`, then *immediately increments* `self.nonce += 1`.
  - When loop finishes, the stored `self.nonce` is **1 greater** than the nonce that produced `self.blockHash`.

### Practical Usage Example
```python
from Blockchain.Backend.Core.blockheader import BlockHeader
from Blockchain.config import TARGET, ZERO_HASH
import time

header = BlockHeader(
    version=1.0,
    prev_block_hash=ZERO_HASH,
    merkle_root="",
    timestamp=int(time.time()),
    bits="ffff0000"
)
header.mine(TARGET)
print("Mined Hash:", header.blockHash)
print("Saved Nonce:", header.nonce)  # Nonce that mined it was header.nonce - 1
```

---

## 5. Block Container (`Backend/Core/block.py`)

### Purpose
Represents a complete block container storing the header, transactions list, and block size.

### Class: `Block`
- **Constructor `__init__(Height, Blocksize, BlockHeader, Txs)`**:
  - `Height`: Integer sequence index of the block ($1, 2, 3, \dots$).
  - `Blocksize`: Block size indicator (default `1`).
  - `BlockHeader`: Dictionary or object of the header.
  - `Txs`: Dictionary or list of transactions inside the block.
  - `Txcount`: Number of transactions in the block (`len(self.Txs)`).

### Practical Usage Example
```python
from Blockchain.Backend.Core.block import Block

new_block = Block(
    Height=1,
    Blocksize=1,
    BlockHeader=header.__dict__,
    Txs=coinbase_tx.to_dict()
)
block_dict = new_block.__dict__
```

---

## 6. Blockchain Manager (`Backend/Core/blockchain.py`)

### Purpose
Coordinates block creation, chain extension, database persistence, and chain validation.

### Class: `Blockchain`
- **`__init__()`**:
  - Initializes `self.blockchainDB = BlockchainDB()`.
  - If database file does not exist, automatically calls `self.create_genesis_block()`.
- **`write_on_disk(block)`**: Writes block list to database.
- **`read_from_disk()`**: Reads all blocks from database.
- **`get_last_block()`**: Returns the latest block dict from disk.
- **`create_genesis_block()`**: Calls `self.add_block(1, ZERO_HASH)`.
- **`add_block(blockHeight, prevBlockHash)`**:
  - Creates a new `CoinbaseTx` for the miner reward.
  - Instantiates `BlockHeader(version, prevBlockHash, merkle_root, timestamp, bits)`.
  - Mines the block via `block_header.mine(TARGET)`.
  - Creates `Block(blockHeight, 1, block_header.__dict__, Txs[0].to_dict())`.
  - Persists the new block to disk via `self.write_on_disk([new_block])`.
- **`add_next_block()`**:
  - Automatically queries `last_block = self.get_last_block()`.
  - Derives `new_block_height = last_block["Height"] + 1`.
  - Derives `new_prev_hash = last_block["BlockHeader"]["blockHash"]`.
  - Mines and appends the new block.
- **`validate_chain(chain=None)`**:
  - Validates empty check, Genesis check, height continuity, parent hash linkage, hash recalculation (using `nonce - 1`), and mining target compliance. Returns `True` if valid, `False` otherwise.
- **`print()`**: Pretty-prints the entire blockchain JSON to terminal.

---

## 7. Scripting System (`Backend/Core/script.py`)

### Purpose
Implements Bitcoin Script (Forth-like stack-based smart contracting language).

### Class: `Script`
- **Constructor `__init__(cmds=None)`**:
  - `cmds`: List of opcodes (integers) and data elements (bytes).
- **Method `serialize()`**:
  - Converts commands into Bitcoin wire-format byte array. Opcodes are stored as 1-byte integers; data elements are prepended by their length opcode (`pushdata`).
- **Classmethod `p2pkh_script(cls, target_public_key)`**:
  - Creates a standard Pay-to-Public-Key-Hash locking script:
    `OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG`
  - In byte opcodes: `[0x76, 0xA9, target_public_key, 0x88, 0xAC]`.

### Practical Usage Example
```python
from Blockchain.Backend.Core.script import Script
from Blockchain.Backend.Util.util import decode_base58

# Create locking script for a recipient address
recipient_address = "15EDkKeKEZRtMiASKZoncU2J8WLqjGk5Hz"
pubkey_hash = decode_base58(recipient_address)
locking_script = Script.p2pkh_script(pubkey_hash)
serialized_script = locking_script.serialize()
```

---

## 8. Transactions & Coinbase (`Backend/Core/tx.py`)

### Purpose
Defines transaction inputs (`TxIn`), transaction outputs (`TxOut`), full transactions (`Tx`), and miner reward issuance (`CoinbaseTx`).

### Classes

#### `CoinbaseTx`
- **Constructor `__init__(BlockHeight)`**: Converts block height to little-endian bytes.
- **Method `CoinbaseTransaction()`**:
  - Input: `prev_tx = ZERO_HASH_BYTES`, `prev_index = 0xFFFFFFFF`.
  - Output: `amount = CURRENT_REWARD * ONE_COIN` (50 coins in Poisha) paid to `MINER_PUBLIC_ADDRESS`.
  - Returns a completed `Tx` object with calculated `.TxId`.

#### `Tx`
- **Constructor `__init__(version, tx_ins, tx_outs, locktime)`**:
  - `version`: 4 bytes little-endian integer.
  - `tx_ins`: List of `TxIn` objects.
  - `tx_outs`: List of `TxOut` objects.
  - `locktime`: 4 bytes little-endian integer (earliest time/block the tx can be mined).
- **`id()`**: Returns the 32-byte transaction hash in reverse hex format: `hash256_bytes(serialize())[::-1].hex()`.
- **`serialize()`**: Returns the transaction in raw binary byte format (version + varint in_count + inputs + varint out_count + outputs + locktime).
- **`is_coinbase()`**: Returns `True` if `len(tx_ins) == 1`, `prev_tx == ZERO_HASH_BYTES`, and `prev_index == 0xFFFFFFFF`.
- **`to_dict()`**: Recursively converts the transaction, inputs, and outputs to standard serializable JSON dictionary.

#### `TxIn` (Transaction Input)
- **Attributes**:
  - `prev_tx`: 32-byte hash of the transaction containing the UTXO being spent.
  - `prev_index`: Integer index of the output in `prev_tx` (0-indexed).
  - `script_sig`: `Script` object unlocking the UTXO (contains signature + public key).
  - `sequence`: Integer sequence number (default `0xFFFFFFFF`).

#### `TxOut` (Transaction Output)
- **Attributes**:
  - `amount`: Integer amount in Poisha (Satoshis).
  - `script_pubkey`: `Script` object specifying the spending condition (locking script).

---

## 9. Elliptic Curve Cryptography (`Backend/Core/EllepticCurve/`)

### Purpose
Implements Secp256k1 Elliptic Curve cryptography ($y^2 = x^3 + 7 \pmod p$), private key generation, ECDSA signing, public key derivation, and signature verification.

### Core Classes & Constants
- `P = 2**256 - 2**32 - 977`: Prime modulus of Secp256k1 field.
- `N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141`: Order of generator group.
- `G = Sha256Point(...)`: Generator point on the curve.

#### `FieldElement(num, prime)`
- Performs finite field arithmetic modulo `prime`: addition (`+`), subtraction (`-`), multiplication (`*`), exponentiation (`**`), division (`/` via Fermat's Little Theorem: $n^{p-2} \pmod p$).

#### `Point(x, y, a, b)`
- Represents point on elliptic curve $y^2 = x^3 + ax + b$.
- Implements point addition (`+`) and scalar point multiplication (`*` via double-and-add algorithm). Handles point at infinity (`Point(None, None, a, b)`).

#### `Sha256Point(x, y)`
- Point on Secp256k1 ($a=0, b=7$).
- `sec(compressed=True)`: Serializes public key point into SEC binary format:
  - Compressed: `b'\x02'` (if $y$ even) or `b'\x03'` (if $y$ odd) followed by 32-byte $x$. (Total 33 bytes).
  - Uncompressed: `b'\x04'` followed by 32-byte $x$ and 32-byte $y$. (Total 65 bytes).
- `hash160(compressed=True)`: RIPEMD160(SHA256(SEC)).
- `address(compressed=True, testnet=False)`: Returns Base58Check address string.
- `verify(z, sig)`: ECDSA signature verification for hash $z$ and signature `sig` $(r, s)$:
  $$u = z \cdot s^{-1} \pmod N, \quad v = r \cdot s^{-1} \pmod N$$
  $$\text{Check if } (u \cdot G + v \cdot P).x == r$$

#### `PrivateKey(secret)`
- Represents ECDSA private key (256-bit secret integer).
- `self.point = secret * G`: Automatically computes the public key point!
- `sign(z)`: Generates ECDSA signature $(r, s)$ for message digest $z$ using deterministic nonce $k$ (RFC 6979).

#### `Signature(r, s)`
- Represents ECDSA signature pair $(r, s)$.
- `der()`: Encodes signature into standard ASN.1 DER byte format (`0x30 [len] 0x02 [rlen] [r] 0x02 [slen] [s]`).

### Practical Cryptography Usage Example
```python
import secrets
from Blockchain.Backend.Core.EllepticCurve.EllepticCurve import PrivateKey, G
from Blockchain.Backend.Util.util import hash256_bytes

# 1. Generate Private Key
secret = secrets.randbits(256)
priv = PrivateKey(secret)

# 2. Public Key point & Address
pub_point = priv.point
address = pub_point.address(compressed=True)
print("Address:", address)

# 3. Sign a message hash z
message = b"Send 10 UAP coins"
z = int.from_bytes(hash256_bytes(message), "big")
signature = priv.sign(z)
print("Signature:", signature.r, signature.s)

# 4. Verify signature using Public Key Point
is_valid = pub_point.verify(z, signature)
print("Signature Valid?", is_valid)  # True!
```

---

## 10. Client Key & Address Generation (`Client/account.py`)

### Purpose
Demonstrates how raw client wallets generate private keys, compute compressed public keys, apply Hash160, attach network prefixes, compute 4-byte double SHA-256 checksums, and encode into Base58 addresses.

---

## 11. Script Opcodes Engine (`Backend/Core/EllepticCurve/op.py`)

### Purpose
Executes individual stack opcodes for validating Bitcoin scripts.

- `op_dup(stack)`: Duplicates the top stack item (`stack.append(stack[-1])`).
- `op_hash160(stack)`: Pops top item, calculates RIPEMD160(SHA256(item)), pushes result.
- `op_equalverify(stack)`: Pops two items, verifies they are equal.
- `op_checksig(stack, z)`: Pops public key and DER signature, parses them, and calls `point.verify(z, sig)`. Pushes 1 if signature valid, 0 otherwise.

---

# PART 2: POSSIBLE EXAM QUESTIONS WITH DETAILED ANSWERS

---

### Question 1: Blockchain Verification with Tamper Localization
**Exam Prompt:**
> "Write a function `locate_chain_fault(chain)` that iterates through a blockchain list and returns either `'VALID'` or a descriptive error tuple `(error_type, block_height, details)` pinpointing the first corrupted block."

**Answer Code:**
```python
from Blockchain.config import TARGET, ZERO_HASH
from Blockchain.Backend.Util.util import hash256

def locate_chain_fault(chain):
    if not chain or len(chain) == 0:
        return ("EMPTY_CHAIN", 0, "Blockchain is empty")

    # Genesis check
    if chain[0].get("Height") != 1:
        return ("GENESIS_HEIGHT_ERROR", chain[0].get("Height"), "Genesis block height must be 1")
    if chain[0]["BlockHeader"].get("prev_block_hash") != ZERO_HASH:
        return ("GENESIS_HASH_ERROR", 1, "Genesis previous hash must be ZERO_HASH")

    for i in range(len(chain)):
        block = chain[i]
        header = block["BlockHeader"]
        height = block["Height"]

        # 1. Height check
        if height != i + 1:
            return ("INVALID_HEIGHT_SEQUENCE", height, f"Block at index {i} has height {height}")

        # 2. Previous hash check
        if i > 0:
            prev_hash = chain[i-1]["BlockHeader"]["blockHash"]
            if header["prev_block_hash"] != prev_hash:
                return ("BROKEN_CHAIN_LINK", height, f"prev_block_hash does not match parent block {i}'s hash")

        # 3. Hash recalculation check (using stored_nonce - 1)
        actual_nonce = header["nonce"] - 1
        raw_header = (
            str(header["version"]) +
            str(header["prev_block_hash"]) +
            str(header.get("merkle_root", "")) +
            str(header["timestamp"]) +
            str(header["bits"]) +
            str(actual_nonce)
        )
        calculated_hash = hash256(raw_header.encode("utf-8"))
        if calculated_hash != header["blockHash"]:
            return ("HASH_MISMATCH", height, f"Recalculated {calculated_hash} != stored {header['blockHash']}")

        # 4. Proof of work target check
        if header["blockHash"][:len(TARGET)] != TARGET:
            return ("TARGET_UNMET", height, f"Hash {header['blockHash']} does not meet target {TARGET}")

    return "VALID"
```
**Explanation:** Tests every invariant in order: Genesis height $\rightarrow$ Genesis parent pointer $\rightarrow$ Height sequence $\rightarrow$ Parent hash linkage $\rightarrow$ SHA-256 header re-hash with `nonce - 1` $\rightarrow$ Target prefix check.

---

### Question 2: Computing Merkle Root from Transactions
**Exam Prompt:**
> "Implement `build_merkle_root(tx_id_list)` that calculates the Merkle Root for a list of transaction IDs (hex strings). If a level has an odd number of elements, duplicate the last element. Return `''` if list is empty."

**Answer Code:**
```python
from Blockchain.Backend.Util.util import hash256

def build_merkle_root(tx_ids):
    if not tx_ids:
        return ""
    if len(tx_ids) == 1:
        return tx_ids[0]

    current_hashes = list(tx_ids)
    while len(current_hashes) > 1:
        # If odd number of hashes, duplicate the last one
        if len(current_hashes) % 2 == 1:
            current_hashes.append(current_hashes[-1])

        parent_level = []
        for i in range(0, len(current_hashes), 2):
            combined = (current_hashes[i] + current_hashes[i+1]).encode("utf-8")
            parent_level.append(hash256(combined))

        current_hashes = parent_level

    return current_hashes[0]
```
**Explanation:** If a block has 3 transactions $[A, B, C]$, it duplicates $C$ to form $[A, B, C, C]$. It then computes $H_{AB} = \text{hash}(A+B)$ and $H_{CC} = \text{hash}(C+C)$. Next iteration, it computes $\text{Root} = \text{hash}(H_{AB} + H_{CC})$. Time complexity is $O(N)$ with $O(\log N)$ tree depth.

---

### Question 3: Validating a Pay-To-Public-Key-Hash (P2PKH) Script
**Exam Prompt:**
> "Explain how a P2PKH script is evaluated on the execution stack. Write a function `evaluate_p2pkh(script_sig, script_pubkey, z)` using `op.py` opcodes."

**Answer Code:**
```python
from Blockchain.Backend.Core.EllepticCurve.op import op_dup, op_hash160, op_equalverify, op_checksig

def evaluate_p2pkh(script_sig_cmds, script_pubkey_cmds, z):
    """
    Executes script_sig (signature + public key) followed by
    script_pubkey (OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG)
    """
    stack = []

    # 1. Execute script_sig (pushes DER signature and Public Key)
    for cmd in script_sig_cmds:
        stack.append(cmd)

    # 2. Execute script_pubkey
    i = 0
    while i < len(script_pubkey_cmds):
        cmd = script_pubkey_cmds[i]
        if cmd == 118:  # OP_DUP
            op_dup(stack)
        elif cmd == 169:  # OP_HASH160
            op_hash160(stack)
        elif cmd == 136:  # OP_EQUALVERIFY
            if not op_equalverify(stack):
                return False
        elif cmd == 172:  # OP_CHECKSIG
            if not op_checksig(stack, z):
                return False
        else:
            # Raw data push (the recipient's 20-byte public key hash)
            stack.append(cmd)
        i += 1

    return len(stack) == 1 and stack[0] == 1
```
**Execution Steps on the Stack:**
1. Start: `script_sig` pushes `[sig, pubkey]`.
2. `OP_DUP`: stack becomes `[sig, pubkey, pubkey]`.
3. `OP_HASH160`: pops top `pubkey`, hashes it $\rightarrow$ `[sig, pubkey, hash160(pubkey)]`.
4. Push `target_pubkey_hash`: stack becomes `[sig, pubkey, hash160(pubkey), target_pubkey_hash]`.
5. `OP_EQUALVERIFY`: pops two hashes, checks equality. If equal, stack is `[sig, pubkey]`.
6. `OP_CHECKSIG`: pops `pubkey` and `sig`, verifies ECDSA signature for message $z$. If valid, pushes `1`.

---

### Question 4: Bitcoin/UAP Address Generation Pipeline
**Exam Prompt:**
> "Explain the complete mathematical and encoding pipeline for converting a private key into a public address. What are each of the prefix and checksum components?"

**Answer:**
1. **Private Key ($k$):** A 256-bit randomly generated integer ($1 \le k < N$).
2. **Public Key Point ($P$):** Scalar multiplication with Generator point: $P = k \times G = (x, y)$.
3. **SEC Compression:**
   - If $y$ is even: `b'\x02' + x_bytes` (33 bytes).
   - If $y$ is odd: `b'\x03' + x_bytes` (33 bytes).
4. **Hash160:** RIPEMD160(SHA256(compressed_sec)) $\rightarrow$ 20-byte Public Key Hash (PKH).
5. **Network Prefix:** Prepend Mainnet prefix `b'\x00'` (1 byte) $\rightarrow$ 21 bytes.
6. **Checksum:** Double SHA-256 of the 21 bytes: $\text{SHA256}(\text{SHA256}(\text{prefix} + \text{PKH}))[:4]$ (first 4 bytes).
7. **Combined Payload:** `21_bytes + 4_byte_checksum` (25 bytes).
8. **Base58 Encoding:** Converts 25 bytes into alphanumeric Base58 string (starting with `'1'`).

---

### Question 5: Mining Difficulty Adjustment (Retargeting)
**Exam Prompt:**
> "Write a function `retarget_bits(current_target, elapsed_seconds, target_seconds=1209600)` implementing Bitcoin's difficulty retargeting with the 4x dampening factor."

**Answer Code:**
```python
def retarget_difficulty(current_target_int, elapsed_seconds, target_seconds=1209600):
    # Clamp elapsed time to between 1/4 and 4x of target time
    if elapsed_seconds < target_seconds // 4:
        elapsed_seconds = target_seconds // 4
    elif elapsed_seconds > target_seconds * 4:
        elapsed_seconds = target_seconds * 4

    new_target = (current_target_int * elapsed_seconds) // target_seconds

    # Clamp to maximum target (lowest difficulty)
    max_target = (1 << 224) - 1
    if new_target > max_target:
        new_target = max_target

    return new_target
```
**Explanation:** If miners found blocks twice as fast as expected (`elapsed = target / 2`), `new_target` becomes half of `current_target`, requiring more leading zeros and making mining twice as difficult.

---

### Question 6: Block Reward Halving Calculation
**Exam Prompt:**
> "Write a function `get_miner_reward(block_height)` that calculates the reward in Poisha for any given block height, where initial reward is 50 coins and halves every 210,000 blocks."

**Answer Code:**
```python
from Blockchain.config import INITIAL_REWARD, ONE_COIN

def get_miner_reward(block_height, halving_interval=210000):
    halvings = (block_height - 1) // halving_interval
    if halvings >= 64:
        return 0  # Bit shift beyond 64 bits reaches 0 subsidy
    reward_coins = INITIAL_REWARD >> halvings
    return reward_coins * ONE_COIN
```
**Explanation:** Block 1 has 0 halvings $\rightarrow 50$ coins. Block 210,001 has 1 halving $\rightarrow 25$ coins. Bitwise right-shift `>> 1` is integer division by 2.

---

### Question 7: Re-mining / 51% Attack Cascade Effect
**Exam Prompt:**
> "Why does modifying data in block $k$ invalidate all subsequent blocks $(k+1, k+2, \dots)$? Write a simulation function to repair a chain after tampering."

**Answer Code:**
```python
import copy
from Blockchain.Backend.Util.util import hash256
from Blockchain.config import TARGET

def repair_tampered_chain(chain, tamper_height, new_data):
    repaired_chain = copy.deepcopy(chain)
    start_index = tamper_height - 1

    for i in range(start_index, len(repaired_chain)):
        header = repaired_chain[i]["BlockHeader"]
        
        # Link to previous block's newly computed hash
        if i > start_index:
            header["prev_block_hash"] = repaired_chain[i-1]["BlockHeader"]["blockHash"]

        # Re-mine current block
        nonce = 0
        while True:
            candidate = (
                str(header["version"]) +
                header["prev_block_hash"] +
                header.get("merkle_root", "") +
                str(header["timestamp"]) +
                str(header["bits"]) +
                str(nonce)
            )
            h = hash256(candidate.encode("utf-8"))
            if h.startswith(TARGET):
                header["nonce"] = nonce + 1  # Offset by 1 matching repo convention
                header["blockHash"] = h
                break
            nonce += 1

    return repaired_chain
```
**Theoretical Explanation:**
- Every block commits to the hash of the parent block via `prev_block_hash`.
- Altering block $k$ alters its hash $H_k$.
- Block $k+1$'s header still contains the old $H_k$, breaking the cryptographic chain pointer.
- Updating Block $k+1$'s pointer alters Block $k+1$'s header, breaking its Proof of Work.
- Thus, the attacker must re-mine block $k$ AND every block that follows it. In an active decentralized network, honest nodes mine new blocks faster than a single attacker unless the attacker possesses $>50\%$ of total network hash power.

---

### Question 8: High-Yield Viva / Oral Exam Questions & Short Answers

| Question | Short, High-Scoring Answer |
| :--- | :--- |
| **Why is SHA-256 chosen over MD5 or SHA-1?** | SHA-256 is collision-resistant and pre-image resistant. MD5 and SHA-1 have proven mathematical collision vulnerabilities. |
| **What is the Avalanche Effect?** | Changing a single bit of input flips approximately 50% of the output bits, making hash outputs look completely random and unpredictable. |
| **Why do we hash the block header instead of the entire block body?** | The header is a compact, fixed size (80 bytes), allowing fast hashing during mining. The header contains the `merkle_root`, which cryptographically secures all transactions inside the body. |
| **What does Nonce stand for and why is it needed?** | Nonce = "Number used ONCE". Since header fields like timestamp and prev_hash are mostly static, the nonce is the variable counter incremented to find a hash meeting the target. |
| **What is the significance of `ZERO_HASH` in Genesis block?** | The Genesis block has no predecessor. By convention, its parent hash is 64 zeros (`"0"*64`) to indicate the root of the blockchain ledger. |
| **Why is `stored_nonce - 1` needed in our lab's `validate_chain()`?** | `BlockHeader.mine()` executes `self.nonce += 1` immediately after computing the hash in the loop. Thus, the saved nonce is 1 greater than the nonce that satisfied the target. |
| **What is an orphan block?** | A valid block mined on a shorter branch that is discarded when the network reorganizes to a longer branch following the Longest Chain Rule. |
| **What is a UTXO?** | Unspent Transaction Output. Bitcoin does not use account balances; your balance is the sum of all unspent transaction outputs locked to your public key hash. |

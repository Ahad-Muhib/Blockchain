# Transaction (`tx.py`) Exam Coding Masterfile

> **Exam Focus**: Pure coding only (No viva / No quiz questions). All solutions are ready for direct copy-pasting, tested against your repository, and include line-by-line explanations.

---

## Quick Reference: The Critical Bug in `tx.py` Line 33
In your project's original `Backend/Core/tx.py`, line 33 contains a subtle spelling bug:
```python
# Original buggy line:
tx_ins[0].script_sig.cmds.append(self.BlockHeightIInLittleEndian)  # Notice the two 'I's!
```
Because the constructor initialized `self.BlockHeightInLittleEndian` (with one 'I'), calling `CoinbaseTx.CoinbaseTransaction()` will throw an `AttributeError`!
Whenever an exam asks you to write or fix a Coinbase transaction, **always make sure to use `self.BlockHeightInLittleEndian`** (one 'I') or use our copy-paste functions below.

---

# CODING QUESTION 1: Creating a Coinbase Transaction
### Problem Statement
> Write a function `create_coinbase_transaction(block_height, miner_address, reward_amount=None, extra_nonce=b"")` that generates a valid Coinbase transaction for a new block.
> 
> **Requirements**:
> 1. Input `prev_tx` must be 32 null bytes (`ZERO_HASH_BYTES`).
> 2. Input `prev_index` must be `0xFFFFFFFF`.
> 3. `script_sig` must encode the `block_height` in little-endian bytes.
> 4. Output `amount` must equal the miner subsidy in Poisha (`CURRENT_REWARD * ONE_COIN`).
> 5. Output `script_pubkey` must lock coins to the `miner_address` using P2PKH script.
> 6. Return a complete `Tx` object with its `.TxId` populated.

### Copy-Paste Python Solution
```python
from Blockchain.Backend.Core.tx import Tx, TxIn, TxOut
from Blockchain.Backend.Core.script import Script
from Blockchain.Backend.Util.util import int_to_little_endian, bytes_needed, decode_base58
from Blockchain.config import ZERO_HASH_BYTES, ONE_COIN, CURRENT_REWARD

def create_coinbase_transaction(block_height, miner_address="15EDkKeKEZRtMiASKZoncU2J8WLqjGk5Hz", reward_amount=None, extra_nonce=b""):
    if reward_amount is None:
        reward_amount = CURRENT_REWARD * ONE_COIN

    # 1. Convert block height to little-endian bytes
    height_bytes = int_to_little_endian(block_height, bytes_needed(block_height))

    # 2. Build Coinbase TxIn
    coinbase_in = TxIn(prev_tx=ZERO_HASH_BYTES, prev_index=0xFFFFFFFF)
    coinbase_in.script_sig.cmds.append(height_bytes)
    if extra_nonce:
        coinbase_in.script_sig.cmds.append(extra_nonce)

    # 3. Build Miner TxOut (P2PKH script)
    miner_pkh = decode_base58(miner_address)
    locking_script = Script.p2pkh_script(miner_pkh)
    coinbase_out = TxOut(amount=reward_amount, script_pubkey=locking_script)

    # 4. Construct Transaction
    coinbase_tx = Tx(version=1, tx_ins=[coinbase_in], tx_outs=[coinbase_out], locktime=0)
    coinbase_tx.TxId = coinbase_tx.id()
    return coinbase_tx
```

### Line-by-Line Explanation
1. `height_bytes = int_to_little_endian(block_height, bytes_needed(block_height))`: Encodes the block height into binary byte representation. In Bitcoin (BIP-34), this prevents duplicate coinbase transaction IDs across different blocks.
2. `TxIn(prev_tx=ZERO_HASH_BYTES, prev_index=0xFFFFFFFF)`: Standard Bitcoin rule for newly minted coins. There is no parent transaction (`prev_tx` is 32 zeros) and no output index (`0xFFFFFFFF`).
3. `coinbase_in.script_sig.cmds.append(height_bytes)`: Pushes the height into the input's unlocking script.
4. `Script.p2pkh_script(miner_pkh)`: Creates `OP_DUP OP_HASH160 <miner_pkh> OP_EQUALVERIFY OP_CHECKSIG`.
5. `coinbase_tx.TxId = coinbase_tx.id()`: Calculates the SHA-256 transaction hash in reverse hex format.

---

# CODING QUESTION 2: Validating a Coinbase Transaction
### Problem Statement
> Write a function `validate_coinbase_transaction(tx, expected_height, max_allowed_reward)` that returns `(is_valid: bool, error_message: str)` checking all consensus rules for a coinbase transaction.

### Copy-Paste Python Solution
```python
from Blockchain.config import ZERO_HASH_BYTES
from Blockchain.Backend.Util.util import little_endian_to_int

def validate_coinbase_transaction(tx, expected_height, max_allowed_reward):
    # Rule 1: Exactly 1 input
    if not tx.tx_ins or len(tx.tx_ins) != 1:
        return False, "Coinbase transaction must have exactly 1 input"

    tx_in = tx.tx_ins[0]

    # Rule 2: Input must point to ZERO_HASH_BYTES
    if tx_in.prev_tx != ZERO_HASH_BYTES:
        return False, "Coinbase input prev_tx must be 32 zero bytes"

    # Rule 3: Input prev_index must be 0xFFFFFFFF
    if tx_in.prev_index != 0xFFFFFFFF:
        return False, "Coinbase input prev_index must be 0xFFFFFFFF"

    # Rule 4: Verify block height inside script_sig
    if not tx_in.script_sig.cmds:
        return False, "Coinbase script_sig must encode block height"

    height_cmd = tx_in.script_sig.cmds[0]
    if isinstance(height_cmd, bytes):
        extracted_height = little_endian_to_int(height_cmd)
    elif isinstance(height_cmd, int):
        extracted_height = height_cmd
    else:
        return False, "Invalid block height encoding in script_sig"

    if extracted_height != expected_height:
        return False, f"Coinbase height {extracted_height} != expected {expected_height}"

    # Rule 5: Reward must not exceed legal subsidy + fees
    total_out = sum(out.amount for out in tx.tx_outs)
    if total_out > max_allowed_reward:
        return False, f"Coinbase payout ({total_out}) exceeds allowed max ({max_allowed_reward})"

    return True, "Valid Coinbase transaction"
```

---

# CODING QUESTION 3: Creating a Standard P2PKH Transfer Transaction (with Change & Fee)
### Problem Statement
> Write a function `create_p2pkh_transaction(sender_utxos, recipient_address, send_amount, change_address, fee=1000000)` that creates a valid Bitcoin/UAP Coin transfer transaction from Alice to Bob, generating change back to Alice and leaving a miner fee.

### Copy-Paste Python Solution
```python
from Blockchain.Backend.Core.tx import Tx, TxIn, TxOut
from Blockchain.Backend.Core.script import Script
from Blockchain.Backend.Util.util import decode_base58

def create_p2pkh_transaction(sender_utxos, recipient_address, send_amount, change_address, fee=1000000):
    """
    sender_utxos format:
    [{ "tx_id": "c5f13292...", "index": 0, "amount": 5000000000 }, ...]
    """
    total_needed = send_amount + fee
    selected_utxos = []
    total_input = 0

    # 1. Greedy selection of UTXOs to cover send_amount + fee
    for utxo in sender_utxos:
        selected_utxos.append(utxo)
        total_input += utxo["amount"]
        if total_input >= total_needed:
            break

    if total_input < total_needed:
        raise ValueError(f"Insufficient funds: available {total_input}, needed {total_needed}")

    # 2. Build TxIns
    tx_ins = []
    for utxo in selected_utxos:
        prev_tx_bytes = bytes.fromhex(utxo["tx_id"])[::-1]  # Stored in reverse little-endian order
        tx_in = TxIn(prev_tx=prev_tx_bytes, prev_index=utxo["index"])
        tx_ins.append(tx_in)

    # 3. Build TxOuts
    tx_outs = []
    # (a) Output for recipient
    recipient_pkh = decode_base58(recipient_address)
    tx_outs.append(TxOut(amount=send_amount, script_pubkey=Script.p2pkh_script(recipient_pkh)))

    # (b) Output for change
    change_amount = total_input - send_amount - fee
    if change_amount > 0:
        change_pkh = decode_base58(change_address)
        tx_outs.append(TxOut(amount=change_amount, script_pubkey=Script.p2pkh_script(change_pkh)))

    # 4. Construct Tx
    tx = Tx(version=1, tx_ins=tx_ins, tx_outs=tx_outs, locktime=0)
    tx.TxId = tx.id()
    return tx
```

---

# CODING QUESTION 4: Transaction Fee Calculation
### Problem Statement
> In Bitcoin, transaction fees are not explicitly specified in the transaction. Write a function `calculate_transaction_fee(tx, utxo_pool)` that looks up the inputs in `utxo_pool` and computes:
> $$\text{Fee} = \sum \text{Input Amounts} - \sum \text{Output Amounts}$$

### Copy-Paste Python Solution
```python
def calculate_transaction_fee(tx, utxo_pool):
    """
    utxo_pool format:
    { (tx_id_hex, output_index): { "amount": 5000000000, ... }, ... }
    """
    # Coinbase transactions create new coins, so fee is 0
    if tx.is_coinbase():
        return 0

    total_in = 0
    for tx_in in tx.tx_ins:
        prev_id_hex = tx_in.prev_tx[::-1].hex()
        key = (prev_id_hex, tx_in.prev_index)

        if key not in utxo_pool:
            raise ValueError(f"Missing UTXO {key} (Spent or invalid)")

        total_in += utxo_pool[key]["amount"]

    total_out = sum(out.amount for out in tx.tx_outs)

    if total_in < total_out:
        raise ValueError(f"Outputs ({total_out}) exceed inputs ({total_in})")

    return total_in - total_out
```

---

# CODING QUESTION 5: Deserializing / Parsing a Raw Transaction from Hex/Bytes
### Problem Statement
> Write a function `parse_raw_transaction(raw_bytes_or_hex)` that parses a raw serialized Bitcoin wire-format transaction back into a `Tx` object.

### Copy-Paste Python Solution
```python
import io
from Blockchain.Backend.Core.tx import Tx, TxIn, TxOut
from Blockchain.Backend.Core.script import Script
from Blockchain.Backend.Util.util import little_endian_to_int, read_varint

def parse_script(stream):
    """Helper to parse a serialized script according to pushdata opcodes."""
    script_len = read_varint(stream)
    raw = stream.read(script_len)
    cmds = []
    s = io.BytesIO(raw)
    while s.tell() < script_len:
        b = s.read(1)[0]
        if b < 76:
            cmds.append(s.read(b))
        elif b == 76:
            data_len = s.read(1)[0]
            cmds.append(s.read(data_len))
        elif b == 77:
            data_len = little_endian_to_int(s.read(2))
            cmds.append(s.read(data_len))
        else:
            cmds.append(b)
    return Script(cmds)

def parse_raw_transaction(raw_bytes_or_hex):
    if isinstance(raw_bytes_or_hex, str):
        stream = io.BytesIO(bytes.fromhex(raw_bytes_or_hex))
    else:
        stream = io.BytesIO(raw_bytes_or_hex)

    # 1. Version (4 bytes)
    version = little_endian_to_int(stream.read(4))

    # 2. Inputs (varint count)
    num_inputs = read_varint(stream)
    tx_ins = []
    for _ in range(num_inputs):
        prev_tx = stream.read(32)[::-1]  # Re-reverse internal byte order
        prev_index = little_endian_to_int(stream.read(4))
        script_sig = parse_script(stream)
        sequence = little_endian_to_int(stream.read(4))
        tx_ins.append(TxIn(prev_tx, prev_index, script_sig, sequence))

    # 3. Outputs (varint count)
    num_outputs = read_varint(stream)
    tx_outs = []
    for _ in range(num_outputs):
        amount = little_endian_to_int(stream.read(8))
        script_pubkey = parse_script(stream)
        tx_outs.append(TxOut(amount, script_pubkey))

    # 4. Locktime (4 bytes)
    locktime = little_endian_to_int(stream.read(4))

    tx = Tx(version, tx_ins, tx_outs, locktime)
    tx.TxId = tx.id()
    return tx
```

---

# CODING QUESTION 6: In-Memory UTXO Pool Manager
### Problem Statement
> Implement a class `UTXOPool` to track unspent transaction outputs, compute balances, and apply valid transactions.

### Copy-Paste Python Solution
```python
from Blockchain.Backend.Core.script import Script

class UTXOPool:
    def __init__(self):
        # Format: (tx_id_hex, output_index) -> { "amount": int, "script_pubkey": Script }
        self.pool = {}

    def add_utxo(self, tx_id_hex, output_index, amount, script_pubkey):
        self.pool[(tx_id_hex, output_index)] = {
            "amount": amount,
            "script_pubkey": script_pubkey
        }

    def spend_utxo(self, tx_id_hex, output_index):
        key = (tx_id_hex, output_index)
        if key not in self.pool:
            raise ValueError(f"UTXO {key} already spent or does not exist!")
        del self.pool[key]

    def contains(self, tx_id_hex, output_index):
        return (tx_id_hex, output_index) in self.pool

    def get_balance(self, public_key_hash_bytes):
        target_script = Script.p2pkh_script(public_key_hash_bytes).serialize()
        total = 0
        for utxo in self.pool.values():
            if utxo["script_pubkey"].serialize() == target_script:
                total += utxo["amount"]
        return total

    def apply_transaction(self, tx):
        tx_id_hex = tx.id()
        # Remove spent outputs (unless coinbase)
        if not tx.is_coinbase():
            for tx_in in tx.tx_ins:
                prev_id = tx_in.prev_tx[::-1].hex()
                self.spend_utxo(prev_id, tx_in.prev_index)

        # Insert newly created outputs
        for idx, tx_out in enumerate(tx.tx_outs):
            self.add_utxo(tx_id_hex, idx, tx_out.amount, tx_out.script_pubkey)
```

---

# CODING QUESTION 7: Validating All Transactions in a Block
### Problem Statement
> Implement `validate_block_transactions(tx_list, block_height, utxo_pool, base_reward)` to verify:
> 1. Transaction list is non-empty.
> 2. First transaction is Coinbase; no other transaction is Coinbase.
> 3. No inputs are double-spent within the block.
> 4. All regular transaction inputs exist in `utxo_pool`.
> 5. Coinbase reward $\le \text{base\_reward} + \sum \text{fees}$.

### Copy-Paste Python Solution
```python
from Blockchain.config import ONE_COIN

def validate_block_transactions(tx_list, block_height, utxo_pool, base_reward=50*ONE_COIN):
    if not tx_list:
        return False, "Block has no transactions"

    coinbase_tx = tx_list[0]
    if not coinbase_tx.is_coinbase():
        return False, "First transaction in block MUST be Coinbase"

    total_fees = 0
    spent_in_block = set()

    for i in range(1, len(tx_list)):
        tx = tx_list[i]
        if tx.is_coinbase():
            return False, f"Transaction at index {i} cannot be Coinbase"

        total_in = 0
        for tx_in in tx.tx_ins:
            prev_id = tx_in.prev_tx[::-1].hex()
            key = (prev_id, tx_in.prev_index)

            # Check within-block double spend
            if key in spent_in_block:
                return False, f"Double-spend detected within block for UTXO {key}"
            spent_in_block.add(key)

            # Check existence in UTXO pool
            if not utxo_pool.contains(prev_id, tx_in.prev_index):
                return False, f"UTXO {key} not found in UTXO pool"

            total_in += utxo_pool.pool[key]["amount"]

        total_out = sum(out.amount for out in tx.tx_outs)
        if total_in < total_out:
            return False, f"Transaction at index {i} has outputs > inputs"

        total_fees += (total_in - total_out)

    # Validate Coinbase subsidy + fees
    max_reward = base_reward + total_fees
    is_cb_valid, msg = validate_coinbase_transaction(coinbase_tx, block_height, max_reward)
    if not is_cb_valid:
        return False, f"Coinbase invalid: {msg}"

    return True, "All transactions in block are valid"
```

---

# CODING QUESTION 8: Double-Spending Detection in Mempool
### Problem Statement
> Write a function `detect_mempool_conflicts(pending_txs)` that checks a list of unconfirmed transactions and returns a list of all transactions that conflict (attempting to spend the same UTXO).

### Copy-Paste Python Solution
```python
def detect_mempool_conflicts(pending_txs):
    seen_utxos = {}
    conflicting_txs = set()

    for tx in pending_txs:
        if tx.is_coinbase():
            continue

        for tx_in in tx.tx_ins:
            prev_id = tx_in.prev_tx[::-1].hex()
            key = (prev_id, tx_in.prev_index)

            if key in seen_utxos:
                conflicting_txs.add(tx.id())
                conflicting_txs.add(seen_utxos[key])
            else:
                seen_utxos[key] = tx.id()

    return list(conflicting_txs)
```

---

# CODING QUESTION 9: Multi-Input UTXO Consolidation
### Problem Statement
> Write a function `consolidate_utxos(sender_utxos, destination_address, fee=1000000)` that combines all available UTXOs into a single output to save future transaction fees.

### Copy-Paste Python Solution
```python
from Blockchain.Backend.Core.tx import Tx, TxIn, TxOut
from Blockchain.Backend.Core.script import Script
from Blockchain.Backend.Util.util import decode_base58

def consolidate_utxos(sender_utxos, destination_address, fee=1000000):
    total_input = sum(utxo["amount"] for utxo in sender_utxos)
    if total_input <= fee:
        raise ValueError("UTXO balance cannot even cover the fee!")

    send_amount = total_input - fee

    tx_ins = []
    for utxo in sender_utxos:
        prev_tx_bytes = bytes.fromhex(utxo["tx_id"])[::-1]
        tx_ins.append(TxIn(prev_tx=prev_tx_bytes, prev_index=utxo["index"]))

    dest_pkh = decode_base58(destination_address)
    tx_outs = [TxOut(amount=send_amount, script_pubkey=Script.p2pkh_script(dest_pkh))]

    tx = Tx(version=1, tx_ins=tx_ins, tx_outs=tx_outs, locktime=0)
    tx.TxId = tx.id()
    return tx
```

---

# Verification & Test Script
All functions above are implemented and verified in [tx_exam_practice_code.py](file:///c:/Users/muhib/Desktop/Blockchain/solved%20questions/tx_exam_practice_code.py).
Run the test script to verify:
```bash
python "solved questions/tx_exam_practice_code.py"
```
Output:
```
ALL TRANSACTION PRACTICE TESTS COMPLETED SUCCESSFULLY!
```

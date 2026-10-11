import sys
import os
import io
import copy

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
parent_root = os.path.dirname(project_root)

for path in [current_dir, project_root, parent_root, "C:/Users/muhib/Desktop"]:
    if path not in sys.path:
        sys.path.insert(0, path)

from Blockchain.Backend.Core.tx import Tx, TxIn, TxOut, CoinbaseTx
from Blockchain.Backend.Core.script import Script
from Blockchain.Backend.Util.util import (
    hash256,
    hash256_bytes,
    int_to_little_endian,
    little_endian_to_int,
    encode_varint,
    read_varint,
    decode_base58,
    bytes_needed
)
from Blockchain.config import ONE_COIN, ZERO_HASH_BYTES, CURRENT_REWARD, INITIAL_REWARD
from Blockchain.Backend.Core.EllepticCurve.EllepticCurve import PrivateKey, Sha256Point, Signature, G


# ==============================================================================
# SCRIPT PARSER HELPER (Used for Deserialization)
# ==============================================================================
def parse_script(stream):
    """
    Parses a serialized Script from a byte stream:
    Reads varint script length, then parses opcodes (integers)
    and data elements (bytes) according to pushdata rules.
    """
    script_len = read_varint(stream)
    raw = stream.read(script_len)
    cmds = []
    s = io.BytesIO(raw)
    while s.tell() < script_len:
        b = s.read(1)[0]
        # Data push up to 75 bytes
        if b < 76:
            cmds.append(s.read(b))
        elif b == 76:  # pushdata 1
            data_len = s.read(1)[0]
            cmds.append(s.read(data_len))
        elif b == 77:  # pushdata 2
            data_len = little_endian_to_int(s.read(2))
            cmds.append(s.read(data_len))
        else:  # Standard opcode (e.g. 118 OP_DUP, 169 OP_HASH160, 136 OP_EQUALVERIFY, 172 OP_CHECKSIG)
            cmds.append(b)
    return Script(cmds)


# ==============================================================================
# QUESTION 1: Robust Coinbase Transaction Creator (Fixing the codebase typo)
# ==============================================================================
def create_coinbase_transaction(block_height, miner_address="15EDkKeKEZRtMiASKZoncU2J8WLqjGk5Hz", reward_amount=None, extra_nonce=b""):
    """
    Creates a valid Coinbase Transaction for a block.
    
    Fixes the typo in the original tx.py line 33 (BlockHeightIInLittleEndian -> BlockHeightInLittleEndian)
    and allows flexible miner addresses and reward amounts.
    
    Structure:
    - Input: prev_tx = 32 zero bytes (ZERO_HASH_BYTES), prev_index = 0xFFFFFFFF
    - script_sig: contains block_height in little endian + optional extra_nonce
    - Output: amount in Poisha (Satoshis) paid to miner's P2PKH script
    """
    if reward_amount is None:
        reward_amount = CURRENT_REWARD * ONE_COIN

    # 1. Encode block height in little-endian
    height_bytes = int_to_little_endian(block_height, bytes_needed(block_height))

    # 2. Construct Coinbase Input
    coinbase_in = TxIn(ZERO_HASH_BYTES, 0xFFFFFFFF)
    coinbase_in.script_sig.cmds.append(height_bytes)
    if extra_nonce:
        coinbase_in.script_sig.cmds.append(extra_nonce)

    # 3. Construct Miner Output (P2PKH script)
    miner_pubkey_hash = decode_base58(miner_address)
    locking_script = Script.p2pkh_script(miner_pubkey_hash)
    coinbase_out = TxOut(amount=reward_amount, script_pubkey=locking_script)

    # 4. Create and ID the Transaction
    coinbase_tx = Tx(version=1, tx_ins=[coinbase_in], tx_outs=[coinbase_out], locktime=0)
    coinbase_tx.TxId = coinbase_tx.id()
    return coinbase_tx


# ==============================================================================
# QUESTION 2: Validating a Coinbase Transaction
# ==============================================================================
def validate_coinbase_transaction(tx, expected_height, max_allowed_reward):
    """
    Validates that a transaction is a valid Coinbase Transaction:
    1. Must have exactly 1 input.
    2. Input prev_tx must be 32 zero bytes.
    3. Input prev_index must be 0xFFFFFFFF.
    4. script_sig must contain the expected block height.
    5. Output amount must not exceed max_allowed_reward (subsidy + fees).
    
    Returns: (is_valid: bool, error_message: str)
    """
    if not tx.tx_ins or len(tx.tx_ins) != 1:
        return False, "Coinbase transaction must have exactly 1 input"

    tx_in = tx.tx_ins[0]
    if tx_in.prev_tx != ZERO_HASH_BYTES:
        return False, "Coinbase input prev_tx must be 32 zero bytes"

    if tx_in.prev_index != 0xFFFFFFFF:
        return False, "Coinbase input prev_index must be 0xFFFFFFFF"

    # Verify block height in script_sig
    if not tx_in.script_sig.cmds:
        return False, "Coinbase script_sig must encode block height"

    height_cmd = tx_in.script_sig.cmds[0]
    if isinstance(height_cmd, bytes):
        extracted_height = little_endian_to_int(height_cmd)
    elif isinstance(height_cmd, int):
        extracted_height = height_cmd
    else:
        return False, "Invalid block height format in script_sig"

    if extracted_height != expected_height:
        return False, f"Coinbase height {extracted_height} does not match expected {expected_height}"

    # Verify output amounts
    total_output = sum(out.amount for out in tx.tx_outs)
    if total_output > max_allowed_reward:
        return False, f"Coinbase output {total_output} exceeds allowed reward {max_allowed_reward}"

    return True, "Valid Coinbase transaction"


# ==============================================================================
# QUESTION 3: Creating a Standard P2PKH Transfer Transaction with Change
# ==============================================================================
def create_p2pkh_transaction(sender_utxos, recipient_address, send_amount, change_address, fee=1000000):
    """
    Creates a regular transfer transaction:
    - Selects UTXOs from sender_utxos until total >= send_amount + fee.
    - Creates TxIns referencing the selected UTXOs.
    - Creates TxOut for recipient.
    - Creates TxOut for change back to change_address (if change > 0).
    
    sender_utxos format: list of dicts:
      [{ "tx_id": "...", "index": 0, "amount": 5000000000 }, ...]
    """
    total_needed = send_amount + fee
    selected_utxos = []
    total_input = 0

    for utxo in sender_utxos:
        selected_utxos.append(utxo)
        total_input += utxo["amount"]
        if total_input >= total_needed:
            break

    if total_input < total_needed:
        raise ValueError(f"Insufficient funds! Have {total_input}, need {total_needed}")

    # Build Inputs
    tx_ins = []
    for utxo in selected_utxos:
        prev_tx_bytes = bytes.fromhex(utxo["tx_id"])[::-1]  # Wire format is reversed
        tx_in = TxIn(prev_tx=prev_tx_bytes, prev_index=utxo["index"])
        tx_ins.append(tx_in)

    # Build Outputs
    tx_outs = []
    # 1. Recipient output
    recipient_pkh = decode_base58(recipient_address)
    tx_outs.append(TxOut(amount=send_amount, script_pubkey=Script.p2pkh_script(recipient_pkh)))

    # 2. Change output
    change_amount = total_input - send_amount - fee
    if change_amount > 0:
        change_pkh = decode_base58(change_address)
        tx_outs.append(TxOut(amount=change_amount, script_pubkey=Script.p2pkh_script(change_pkh)))

    tx = Tx(version=1, tx_ins=tx_ins, tx_outs=tx_outs, locktime=0)
    tx.TxId = tx.id()
    return tx


# ==============================================================================
# QUESTION 4: Transaction Fee Calculation
# ==============================================================================
def calculate_transaction_fee(tx, utxo_pool):
    """
    Calculates the transaction fee:
    fee = sum(inputs) - sum(outputs)
    
    utxo_pool format:
      { (tx_id_hex, output_index): { "amount": 5000000000, ... }, ... }
    """
    if tx.is_coinbase():
        return 0  # Coinbase tx does not spend inputs

    total_in = 0
    for tx_in in tx.tx_ins:
        tx_id_hex = tx_in.prev_tx[::-1].hex()
        key = (tx_id_hex, tx_in.prev_index)
        if key not in utxo_pool:
            raise ValueError(f"Referenced UTXO {key} not found in UTXO pool (Double-spend or invalid tx)")
        total_in += utxo_pool[key]["amount"]

    total_out = sum(out.amount for out in tx.tx_outs)
    if total_in < total_out:
        raise ValueError(f"Invalid transaction: outputs ({total_out}) exceed inputs ({total_in})")

    return total_in - total_out


# ==============================================================================
# QUESTION 5: Parsing a Raw Serialized Transaction from Bytes
# ==============================================================================
def parse_raw_transaction(raw_bytes_or_hex):
    """
    Deserializes a binary/hex Bitcoin transaction back into a Tx object.
    Mirrors Tx.serialize().
    
    Wire Format:
    - 4 bytes version (little-endian)
    - varint num_inputs
    - for each input:
        - 32 bytes prev_tx (little-endian)
        - 4 bytes prev_index (little-endian)
        - script_sig (varint length + cmds)
        - 4 bytes sequence (little-endian)
    - varint num_outputs
    - for each output:
        - 8 bytes amount (little-endian)
        - script_pubkey (varint length + cmds)
    - 4 bytes locktime (little-endian)
    """
    if isinstance(raw_bytes_or_hex, str):
        stream = io.BytesIO(bytes.fromhex(raw_bytes_or_hex))
    else:
        stream = io.BytesIO(raw_bytes_or_hex)

    version = little_endian_to_int(stream.read(4))

    # Read Inputs
    num_inputs = read_varint(stream)
    tx_ins = []
    for _ in range(num_inputs):
        prev_tx = stream.read(32)[::-1]  # Reverse to restore internal byte order
        prev_index = little_endian_to_int(stream.read(4))
        script_sig = parse_script(stream)
        sequence = little_endian_to_int(stream.read(4))
        tx_ins.append(TxIn(prev_tx, prev_index, script_sig, sequence))

    # Read Outputs
    num_outputs = read_varint(stream)
    tx_outs = []
    for _ in range(num_outputs):
        amount = little_endian_to_int(stream.read(8))
        script_pubkey = parse_script(stream)
        tx_outs.append(TxOut(amount, script_pubkey))

    locktime = little_endian_to_int(stream.read(4))

    tx = Tx(version, tx_ins, tx_outs, locktime)
    tx.TxId = tx.id()
    return tx


# ==============================================================================
# QUESTION 6: UTXO Pool State Manager
# ==============================================================================
class UTXOPool:
    """
    Tracks Unspent Transaction Outputs (UTXO Set) in memory.
    Key: (tx_id_hex, output_index)
    Value: { 'amount': int, 'script_pubkey': Script }
    """
    def __init__(self):
        self.pool = {}

    def add_utxo(self, tx_id_hex, output_index, amount, script_pubkey):
        self.pool[(tx_id_hex, output_index)] = {
            "amount": amount,
            "script_pubkey": script_pubkey
        }

    def spend_utxo(self, tx_id_hex, output_index):
        key = (tx_id_hex, output_index)
        if key not in self.pool:
            raise ValueError(f"Cannot spend non-existent UTXO: {key}")
        del self.pool[key]

    def contains(self, tx_id_hex, output_index):
        return (tx_id_hex, output_index) in self.pool

    def get_balance(self, public_key_hash_bytes):
        """Calculates total balance for a given public key hash."""
        target_script = Script.p2pkh_script(public_key_hash_bytes).serialize()
        total = 0
        for utxo in self.pool.values():
            if utxo["script_pubkey"].serialize() == target_script:
                total += utxo["amount"]
        return total

    def apply_transaction(self, tx):
        """
        Validates transaction against pool, removes spent UTXOs,
        and adds new transaction outputs to the pool.
        """
        tx_id_hex = tx.id()

        # 1. If not coinbase, remove spent UTXOs
        if not tx.is_coinbase():
            for tx_in in tx.tx_ins:
                prev_id = tx_in.prev_tx[::-1].hex()
                self.spend_utxo(prev_id, tx_in.prev_index)

        # 2. Add new outputs
        for idx, tx_out in enumerate(tx.tx_outs):
            self.add_utxo(tx_id_hex, idx, tx_out.amount, tx_out.script_pubkey)


# ==============================================================================
# QUESTION 7: Validating All Transactions Inside a Block
# ==============================================================================
def validate_block_transactions(tx_list, block_height, utxo_pool, base_reward=50*ONE_COIN):
    """
    Validates all transactions in a block:
    1. List must not be empty.
    2. First tx must be Coinbase.
    3. No other tx can be Coinbase.
    4. All regular txs must reference valid UTXOs without double-spending.
    5. Coinbase reward <= base_reward + total_fees.
    
    Returns: (is_valid: bool, error_message: str)
    """
    if not tx_list:
        return False, "Block has no transactions"

    coinbase_tx = tx_list[0]
    if not coinbase_tx.is_coinbase():
        return False, "First transaction in block MUST be Coinbase"

    total_fees = 0
    spent_in_this_block = set()

    # Verify regular transactions (index 1 onwards)
    for i in range(1, len(tx_list)):
        tx = tx_list[i]
        if tx.is_coinbase():
            return False, f"Transaction at index {i} cannot be Coinbase"

        # Check inputs
        total_in = 0
        for tx_in in tx.tx_ins:
            prev_id = tx_in.prev_tx[::-1].hex()
            utxo_key = (prev_id, tx_in.prev_index)

            # Check within-block double spend
            if utxo_key in spent_in_this_block:
                return False, f"Double-spend detected within block on UTXO {utxo_key}"
            spent_in_this_block.add(utxo_key)

            # Check UTXO exists in pool
            if not utxo_pool.contains(prev_id, tx_in.prev_index):
                return False, f"UTXO {utxo_key} not found in UTXO pool"

            total_in += utxo_pool.pool[utxo_key]["amount"]

        total_out = sum(out.amount for out in tx.tx_outs)
        if total_in < total_out:
            return False, f"Transaction outputs ({total_out}) exceed inputs ({total_in})"

        total_fees += (total_in - total_out)

    # Validate Coinbase subsidy + fees
    max_allowed = base_reward + total_fees
    is_cb_valid, cb_msg = validate_coinbase_transaction(coinbase_tx, block_height, max_allowed)
    if not is_cb_valid:
        return False, f"Coinbase validation failed: {cb_msg}"

    return True, "All transactions in block are valid"


# ==============================================================================
# TEST RUNNER & VERIFICATION
# ==============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING TRANSACTION CODING PRACTICE TESTS")
    print("=" * 70)

    # 1. Test Coinbase Creation & Typo Fix
    print("\n--- 1. Testing create_coinbase_transaction() ---")
    miner_addr = "15EDkKeKEZRtMiASKZoncU2J8WLqjGk5Hz"
    cb = create_coinbase_transaction(block_height=5, miner_address=miner_addr)
    print(f"Created Coinbase TxId: {cb.TxId}")
    print(f"Is Coinbase? {cb.is_coinbase()}")
    print(f"Output Amount: {cb.tx_outs[0].amount} Poisha")

    # 2. Test Coinbase Validation
    print("\n--- 2. Testing validate_coinbase_transaction() ---")
    valid_cb, msg = validate_coinbase_transaction(cb, expected_height=5, max_allowed_reward=50*ONE_COIN)
    print(f"Validation Result: {valid_cb} | Reason: {msg}")

    # Test Bad Height
    bad_cb, bad_msg = validate_coinbase_transaction(cb, expected_height=99, max_allowed_reward=50*ONE_COIN)
    print(f"Bad Height Result: {bad_cb} | Reason: {bad_msg}")

    # 3. Test Serialization & Parsing Round-Trip
    print("\n--- 3. Testing Tx.serialize() and parse_raw_transaction() ---")
    serialized_bytes = cb.serialize()
    parsed_tx = parse_raw_transaction(serialized_bytes)
    print(f"Original TxId: {cb.TxId}")
    print(f"Parsed   TxId: {parsed_tx.TxId}")
    print(f"Matches? {cb.TxId == parsed_tx.TxId}")

    # 4. Test UTXO Pool & Transfer Transaction
    print("\n--- 4. Testing UTXO Pool & Transfer Transaction ---")
    pool = UTXOPool()
    # Add a 10 coin UTXO for Alice
    alice_pkh = decode_base58(miner_addr)
    pool.add_utxo("a" * 64, 0, 10 * ONE_COIN, Script.p2pkh_script(alice_pkh))

    # Alice sends 4 coins to Bob, 0.1 coin fee
    user_utxos = [{"tx_id": "a" * 64, "index": 0, "amount": 10 * ONE_COIN}]
    transfer_tx = create_p2pkh_transaction(
        sender_utxos=user_utxos,
        recipient_address=miner_addr,
        send_amount=4 * ONE_COIN,
        change_address=miner_addr,
        fee=10000000  # 0.1 coin
    )
    print(f"Transfer TxId: {transfer_tx.TxId}")
    print(f"Recipient Output: {transfer_tx.tx_outs[0].amount / ONE_COIN} coins")
    print(f"Change Output:    {transfer_tx.tx_outs[1].amount / ONE_COIN} coins")

    # Calculate fee
    fee = calculate_transaction_fee(transfer_tx, pool.pool)
    print(f"Calculated Fee:   {fee} Poisha ({fee / ONE_COIN} coins)")

    # Apply to pool
    pool.apply_transaction(transfer_tx)
    print("UTXO Pool after transfer:", len(pool.pool), "unspent outputs remaining.")

    # 5. Test Block Transaction Validation
    print("\n--- 5. Testing validate_block_transactions() ---")
    # New block with coinbase (collecting 50 subsidy + 0.1 fee) and the transfer tx
    block_cb = create_coinbase_transaction(6, miner_addr, reward_amount=50*ONE_COIN + fee)
    test_pool = UTXOPool()
    test_pool.add_utxo("a" * 64, 0, 10 * ONE_COIN, Script.p2pkh_script(alice_pkh))

    is_block_valid, block_msg = validate_block_transactions(
        tx_list=[block_cb, transfer_tx],
        block_height=6,
        utxo_pool=test_pool,
        base_reward=50*ONE_COIN
    )
    print(f"Block Txs Valid: {is_block_valid} | Message: {block_msg}")

    print("\n" + "=" * 70)
    print("ALL TRANSACTION PRACTICE TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

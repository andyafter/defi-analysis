#!/usr/bin/env python3
"""Test connection to Ethereum RPC."""

from dotenv import load_dotenv
import os
from web3 import Web3
import time

# Load environment variables
load_dotenv()

RPC_URL = os.getenv("ETH_RPC_URL")
print(f"Testing RPC URL: {RPC_URL[:50]}...")

# Test basic connection
try:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    connected = w3.is_connected()
    print(f"Connection status: {connected}")
    
    if connected:
        # Get latest block
        latest_block = w3.eth.block_number
        print(f"Latest block: {latest_block}")
        
        # Get chain ID
        chain_id = w3.eth.chain_id
        print(f"Chain ID: {chain_id}")
        
        # Test the specific blocks from the analysis
        test_block = 17618642
        block = w3.eth.get_block(test_block)
        print(f"Block {test_block} timestamp: {block['timestamp']}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 
import asyncio
import json
import random

from eth_account import Account
from web3 import Web3

from src.multirpc.async_multi_rpc_interface import AsyncMultiRpc
from src.multirpc.constants import ViewPolicy
from src.multirpc.sync_multi_rpc_interface import MultiRpc
from src.tests.constants import ContractAddr, RPCs
from src.tests.test_settings import PrivateKey1, PrivateKey2


async def async_test_map(mr: AsyncMultiRpc, addr: str = None, pk: str = None):
    random_hex = hex(random.randint(0x10, 0xff))
    print(f"Random hex: {random_hex}")
    await mr.functions.set(random_hex).call(address=addr, private_key=pk)

    result: bytes = await mr.functions.map(addr).call()
    result_hex = "0x" + result.hex()
    print(f"map(addr: {addr}): {result_hex}")
    assert random_hex == result_hex, "test was not successful"


async def async_main():
    multi_rpc = AsyncMultiRpc(rpcs, contract_addr, view_policy=ViewPolicy.FirstSuccess, contract_abi=abi,
                              gas_estimation=None, enable_gas_estimation=True)
    await multi_rpc.setup()
    multi_rpc.set_account(address1, private_key=private_key1)

    print(f"tx_receipt: {await multi_rpc.get_tx_receipt(tx_hash)}")
    print(f"block: {await multi_rpc.get_block(block)}")
    print(f"Nonce: {await multi_rpc.get_nonce(address1)}")
    print(f"map(addr): 0x{bytes(await multi_rpc.functions.map(address1).call()).hex()}")

    await async_test_map(multi_rpc, address1)
    await async_test_map(multi_rpc, address2, private_key2)

    print("async test was successful")


def sync_test_map(mr: MultiRpc, addr: str = None, pk: str = None):
    random_hex = hex(random.randint(0x10, 0xff))
    print(f"Random hex: {random_hex}")
    mr.functions.set(random_hex).call(address=addr, private_key=pk)

    result: bytes = mr.functions.map(addr).call()
    result_hex = "0x" + result.hex()
    print(f"map(addr: {addr}): {result_hex}")
    assert random_hex == result_hex, "test was not successful"


def sync_main():
    multi_rpc = MultiRpc(rpcs, contract_addr, contract_abi=abi, gas_estimation=None, enable_gas_estimation=True)
    multi_rpc.set_account(address1, private_key=private_key1)

    print(f"tx_receipt: {multi_rpc.get_tx_receipt(tx_hash)}")
    print(f"block: {multi_rpc.get_block(block)}")
    print(f"Nonce: {multi_rpc.get_nonce(address1)}")
    print(f"map(addr): 0x{bytes(multi_rpc.functions.map(address1).call()).hex()}")

    sync_test_map(multi_rpc, address1)
    sync_test_map(multi_rpc, address2, private_key2)

    print("sync test was successful")


async def test():

    sync_main()
    await async_main()


if __name__ == '__main__':
    private_key1 = PrivateKey1
    private_key2 = PrivateKey2
    address1 = Account.from_key(private_key1).address
    address2 = Account.from_key(private_key2).address
    contract_addr = Web3.to_checksum_address(ContractAddr)
    tx_hash = '0x7bb81aba6b2ea3145034c676e89d4eb0bc2cdc423a95b8b32d50100fe18d90e5'
    block = 69354608

    rpcs = RPCs
    with open("tests/abi.json", "r") as f:
        abi = json.load(f)

    asyncio.run(test())

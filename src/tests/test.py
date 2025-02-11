import asyncio
import logging
import random

from eth_account import Account
from web3.exceptions import MismatchedABI

from src.multirpc.async_multi_rpc_interface import AsyncMultiRpc
from src.multirpc.constants import GasEstimationMethod, ViewPolicy
from src.multirpc.sync_multi_rpc_interface import MultiRpc
from src.multirpc.utils import ChainConfigTest
from src.tests.constants import ArbConfig, BaseConfig, PolyConfig, RPCsSupportingTxTrace, abi
from src.tests.test_settings import LogLevel, PrivateKey1, PrivateKey2

PreviousBlock = 3


async def async_test_map(mr: AsyncMultiRpc, addr: str = None, pk: str = None):
    random_int = random.randint(10, 100)
    print(f"Random int: {random_int}")
    # await mr.functions.set(random_int).call(address=addr, private_key=pk,
    #                                         gas_estimation_method=GasEstimationMethod.GAS_API_PROVIDER)
    # await mr.functions.set(random_int).call(address=addr, private_key=pk,
    #                                         gas_estimation_method=GasEstimationMethod.FIXED)

    # for failure purpose
    try:
        await mr.functions.set(random_int, random_int).call(address=addr, private_key=pk,
                                                            gas_estimation_method=GasEstimationMethod.RPC)
    except MismatchedABI:
        pass

    type(random_int)

    try:
        await mr.functions.set(random.randint(1, 9)
                               ).call(address=addr, private_key=pk,
                                      gas_estimation_method=GasEstimationMethod.RPC,
                                      enable_estimate_gas_limit=False
                                      )
    except Exception as e:
        print(e)

    print(f'encoded function: {mr.functions.set(random_int).get_encoded_data()}')
    tx_receipt = await mr.functions.set(random_int).call(address=addr, private_key=pk,
                                                         gas_estimation_method=GasEstimationMethod.RPC)

    print(f"{tx_receipt=}")
    result = await mr.functions.map(addr).call()
    print(f"map(addr: {addr}): {result}")
    assert random_int == result, "test was not successful"


async def async_main(chain_config: ChainConfigTest):
    multi_rpc = AsyncMultiRpc(chain_config.rpc, chain_config.contract_address,
                              rpcs_supporting_tx_trace=RPCsSupportingTxTrace,
                              view_policy=ViewPolicy.MostUpdated,
                              contract_abi=abi, gas_estimation=None, log_level=LogLevel,
                              is_proof_authority=config_.is_proof_authority,
                              multicall_custom_address=chain_config.multicall_address, enable_estimate_gas_limit=True)
    multi_rpc.set_account(address1, private_key=PrivateKey1)

    p_block = await multi_rpc.get_block_number() - PreviousBlock
    print(f"tx_receipt: {await multi_rpc.get_tx_receipt(chain_config.tx_hash)}")
    print(f"block: {await multi_rpc.get_block(p_block - 1000)}")
    print(f"Nonce: {await multi_rpc.get_nonce(address1)}")
    print(f"map({address1}): {await multi_rpc.functions.map(address1).call()}")

    results = await multi_rpc.functions.map([(address1,), (address2,)] * 100).multicall()
    print(f"map({address1, address2}): {[res for res in results]}")
    print(f"map({address1}) in {p_block=}: "
          f"{await multi_rpc.functions.map(address1).call(block_identifier=p_block)}")

    await async_test_map(multi_rpc, address1)
    # await async_test_map(multi_rpc, address2, PrivateKey2)


def sync_test_map(mr: MultiRpc, addr: str = None, pk: str = None):
    random_int = random.randint(10, 100)
    print(f"Random int: {random_int}")
    print(f'encoded function: {mr.functions.set(random_int).get_encoded_data()}')
    mr.functions.set(random_int).call(address=addr, private_key=pk)

    result = mr.functions.map(addr).call()
    print(f"map(addr: {addr}): {result}")
    assert random_int == result, "test was not successful"


def sync_main(chain_config: ChainConfigTest):
    multi_rpc = MultiRpc(chain_config.rpc, chain_config.contract_address, contract_abi=abi,
                         rpcs_supporting_tx_trace=RPCsSupportingTxTrace,
                         gas_estimation=None,
                         enable_estimate_gas_limit=True, log_level=LogLevel,
                         is_proof_authority=config_.is_proof_authority,
                         multicall_custom_address=chain_config.multicall_address)
    multi_rpc.set_account(address1, private_key=PrivateKey1)

    p_block = multi_rpc.get_block_number() - PreviousBlock
    print(f"tx_receipt: {multi_rpc.get_tx_receipt(chain_config.tx_hash)}")
    print(f"block: {multi_rpc.get_block(p_block - 1000)}")
    print(f"Nonce: {multi_rpc.get_nonce(address1)}")
    print(f"map({address1}): {multi_rpc.functions.map(address1).call()}")

    results = multi_rpc.functions.map([(address1,), (address2,)]).multicall()
    print(f"map({address1, address2}): {[res for res in results]}")
    print(f"map({address1}) in {p_block=}: "
          f"{multi_rpc.functions.map(address1).call(block_identifier=p_block)}")

    sync_test_map(multi_rpc, address1)
    sync_test_map(multi_rpc, address2, PrivateKey2)


async def test(chain_config: ChainConfigTest):
    # try:
    #     sync_main(chain_config)
    #     print("###sync test was successful###")
    # except Exception as e:
    #     logging.error(e)

    try:
        await async_main(chain_config)
        print('###async test was successful###')
    except Exception as e:
        logging.error(e)


if __name__ == '__main__':
    address1 = Account.from_key(PrivateKey1).address
    address2 = Account.from_key(PrivateKey2).address
    for config_ in [
        ArbConfig,
        PolyConfig,
        BaseConfig,
        # MantleConfig
    ]:
        print(f"=============================== Start Testing on {config_.name} ===============================")
        asyncio.run(test(config_))
        print(f"=============================== Test on {config_.name} Completed ===============================\n\n")

import asyncio
import enum
import json
import logging
import time
from functools import reduce
from typing import Dict, List, Tuple, Union

import web3
from web3 import Web3, AsyncWeb3

from src.multirpc.constants import MaxRPCInEachBracket
from src.multirpc.exceptions import MaximumRPCInEachBracketReached, AtLastProvideOneValidRPCInEachBracket


def get_span_proper_label_from_provider(endpoint_uri):
    return endpoint_uri.split("//")[-1].replace(".", "__").replace("/", "__")


def get_unix_time():
    return int(time.time() * 1000)


class TxPriority(enum.Enum):
    Low = "low"
    Medium = "medium"
    High = "high"


class NestedDict:
    def __init__(self, data: Dict = None):
        if data is None:
            data = dict()
        self.data = data

    def __getitem__(self, keys: Union[Tuple[any], any]):
        if not isinstance(keys, tuple):
            keys = (keys,)
        result = self.data
        for key in keys:
            result = result[key]
        return result

    def __setitem__(self, keys: Union[Tuple[any], any], value) -> None:
        if not isinstance(keys, tuple):
            keys = (keys,)
        current_dict = self.data
        for key in keys[:-1]:
            if not isinstance(current_dict.get(key), dict):
                current_dict[key] = {}
            current_dict = current_dict[key]
        current_dict[keys[-1]] = value

    def items(self):
        def get_items_recursive(data, current_keys=()):
            for key, value in data.items():
                if isinstance(value, dict):
                    yield from get_items_recursive(value, current_keys + (key,))
                else:
                    yield current_keys + (key,), value

        return get_items_recursive(self.data)

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return json.dumps(self.data, indent=1)


async def create_web3_from_rpc(rpc_urls: NestedDict) -> NestedDict:
    async def create_web3(rpc: str):
        async_w3: AsyncWeb3
        if rpc.startswith("http"):
            async_w3 = web3.AsyncWeb3(Web3.AsyncHTTPProvider(rpc))
        else:
            async_w3 = web3.AsyncWeb3(Web3.WebsocketProvider(rpc))
        try:
            status = await async_w3.is_connected()
        except asyncio.exceptions.TimeoutError:
            status = False
        return async_w3, status

    providers = NestedDict()
    for key, rpcs in rpc_urls.items():
        valid_rpcs = []

        if len(rpcs) > MaxRPCInEachBracket:
            raise MaximumRPCInEachBracketReached

        for i, rpc in enumerate(rpcs):
            w3, w3_connected = await create_web3(rpc)
            if not w3_connected:
                logging.warning(f"This rpc({rpc}) doesn't work")
                continue
            valid_rpcs.append(w3)

        if len(valid_rpcs) == 0:
            raise AtLastProvideOneValidRPCInEachBracket

        providers[key] = valid_rpcs

    return providers


async def calculate_chain_id(providers: NestedDict) -> int:
    last_error = None
    for key, providers in providers.items():
        for provider in providers:
            try:
                return await asyncio.wait_for(provider.eth.chain_id, timeout=2)
            except asyncio.TimeoutError as e:
                last_error = e
                logging.warning(f"Can't acquire chain id from this RPC {provider.provider.endpoint_uri}")
    raise last_error


def reduce_list_of_list(ls: List[List]) -> List[any]:
    return reduce(lambda ps, p: ps + p, ls)

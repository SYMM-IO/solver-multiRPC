import asyncio
import enum
import json
import logging
import time
from functools import reduce, wraps
from threading import Thread
from typing import Dict, List, Tuple, Union

import aiohttp.client_exceptions
import web3
from web3 import Web3, AsyncWeb3
from web3.middleware import async_geth_poa_middleware

from .constants import MaxRPCInEachBracket
from .exceptions import MaximumRPCInEachBracketReached, AtLastProvideOneValidRPCInEachBracket


def get_span_proper_label_from_provider(endpoint_uri):
    return endpoint_uri.split("//")[-1].replace(".", "__").replace("/", "__")


class ReturnableThread(Thread):
    # This class is a subclass of Thread that allows the thread to return a value.
    def __init__(self, target, args=(), kwargs=None):
        super().__init__(target=target, args=args, kwargs=kwargs)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.result = None

    def run(self) -> None:
        self.result = self.target(*self.args, **self.kwargs)


class ResultEvent(asyncio.Event):
    def __init__(self):
        super().__init__()
        self.result_ = None

    def set_result(self, result):
        self.result_ = result

    def get_result(self):
        return self.result_


def thread_safe(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            asyncio.get_running_loop()
            t = ReturnableThread(target=func, args=args, kwargs=kwargs)
            t.start()
            t.join()
            return t.result
        except RuntimeError:
            return func(*args, **kwargs)

    return wrapper


def get_unix_time():
    return int(time.time() * 1000)


class TxPriority(enum.Enum):
    Low = "low"
    Medium = "medium"
    High = "high"


class ContractFunctionType:
    View = "view"
    Transaction = "transaction"


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

    def get(self, keys, default=None):
        if not isinstance(keys, tuple):
            keys = (keys,)
        current_dict = self.data
        for key in keys:
            try:
                current_dict = current_dict[key]
            except KeyError:
                return default
        return current_dict

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


async def create_web3_from_rpc(rpc_urls: NestedDict, is_proof_of_authority: bool) -> NestedDict:
    async def create_web3(rpc: str):
        async_w3: AsyncWeb3
        if rpc.startswith("http"):
            async_w3 = web3.AsyncWeb3(Web3.AsyncHTTPProvider(rpc))
        else:
            async_w3 = web3.AsyncWeb3(Web3.WebsocketProvider(rpc))
        if is_proof_of_authority:
            async_w3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
        try:
            status = await async_w3.is_connected()
        except (asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientResponseError):
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

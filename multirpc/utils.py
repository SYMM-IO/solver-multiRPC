import asyncio
import enum
import json
import time
import traceback
from dataclasses import dataclass
from functools import reduce, wraps
from threading import Thread
from typing import Any, Dict, List, Tuple, Union

import aiohttp.client_exceptions
from aiohttp import ClientSession, ClientTimeout
from eth_typing import URI
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3, WebSocketProvider
from web3._utils.http import DEFAULT_HTTP_TIMEOUT
from web3._utils.http_session_manager import HTTPSessionManager
from web3.middleware import ExtraDataToPOAMiddleware

from .constants import MaxRPCInEachBracket, MultiRPCLogger
from .exceptions import AtLastProvideOneValidRPCInEachBracket, MaximumRPCInEachBracketReached


def get_span_proper_label_from_provider(endpoint_uri):
    return endpoint_uri.split("//")[-1].replace(".", "__").replace("/", "__")


class ReturnableThread(Thread):
    def __init__(self, target, args=(), kwargs=None):
        super().__init__(target=target, args=args, kwargs=kwargs)
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self.result = None
        self._exception = None

    def run(self) -> None:
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except Exception as e:
            self._exception = e
            traceback.print_exc()

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        if self._exception:
            raise self._exception
        return self.result


def thread_safe(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        event_loop = asyncio._get_running_loop()
        if event_loop is None:
            return func(*args, **kwargs)
        t = ReturnableThread(target=func, args=args, kwargs=kwargs)
        t.start()
        return t.join()

    return wrapper


class ResultEvent(asyncio.Event):
    def __init__(self):
        super().__init__()
        self.result_ = None

    def set_result(self, result):
        self.result_ = result

    def get_result(self):
        return self.result_


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


class MultiRpcHTTPSessionManager(HTTPSessionManager):
    """
     This class extends the default HTTPSessionManager used by Web3 to ensure that
     the aiohttp ClientSession is always closed—even in the case of a failure or
     cancellation. By placing session closure inside a 'finally' block in both
     'async_make_post_request' and 'async_json_make_get_request', we guarantee
     proper cleanup of network connections and resources, preventing potential
     resource leaks or connection pooling issues if an exception is raised during
     the request or the task is cancelled.

     NOTE: It's based on web3==7.7.0 . If you update web3 check if it's compatible.
     """

    async def async_make_post_request(
            self, endpoint_uri: URI, data: Union[bytes, Dict[str, Any]], **kwargs: Any
    ) -> bytes:
        kwargs.setdefault("timeout", ClientTimeout(DEFAULT_HTTP_TIMEOUT))

        session = ClientSession(raise_for_status=True)
        # session = await self.async_cache_and_return_session(      # fixme: original code
        #     endpoint_uri, request_timeout=kwargs["timeout"]
        # )

        try:
            self.logger.debug(f'making post request, {endpoint_uri=}, {kwargs=}')
            response = await session.post(endpoint_uri, **dict(**kwargs, data=data))
            response.raise_for_status()
            return await response.read()
        finally:
            self.logger.debug(f'task is done/canceled, session will close, {session=}')
            if not session.closed:
                await session.close()

    async def async_json_make_get_request(
            self, endpoint_uri: URI, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        kwargs.setdefault("timeout", ClientTimeout(DEFAULT_HTTP_TIMEOUT))

        session = ClientSession(raise_for_status=True)
        # session = await self.async_cache_and_return_session(      # fixme: original code
        #     endpoint_uri, request_timeout=kwargs["timeout"]
        # )

        try:
            response = await session.get(endpoint_uri, *args, **kwargs)
            response.raise_for_status()
            return await response.json()
        finally:
            self.logger.debug(f'task is done/canceled, {session=}')
            if not session.closed:
                await session.close()


class MultiRpcAsyncHTTPProvider(AsyncHTTPProvider):
    """
    NOTE: It's based on web3==7.7.0 . If you update web3 check if it's compatible.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._request_session_manager = MultiRpcHTTPSessionManager()


async def create_web3_from_rpc(rpc_urls: NestedDict, is_proof_of_authority: bool) -> NestedDict:
    async def create_web3(rpc_: str):
        async_w3: AsyncWeb3
        provider_share_configs = dict(
            cache_allowed_requests=True,
            cacheable_requests={'eth_chainId',
                                'web3_clientVersion',
                                'net_version'},
        )
        if rpc_.startswith("http"):
            async_w3 = AsyncWeb3(MultiRpcAsyncHTTPProvider(rpc_, **provider_share_configs))
        else:
            async_w3 = AsyncWeb3(WebSocketProvider(rpc_, **provider_share_configs))
        if is_proof_of_authority:
            async_w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
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
                MultiRPCLogger.warning(f"This rpc({rpc}) doesn't work")
                continue
            valid_rpcs.append(w3)

        if len(valid_rpcs) == 0:
            raise AtLastProvideOneValidRPCInEachBracket

        providers[key] = valid_rpcs

    return providers


async def get_chain_id(providers: NestedDict) -> int:
    last_error = None
    for key, providers in providers.items():
        for provider in providers:
            try:
                return await asyncio.wait_for(provider.eth.chain_id, timeout=2)
            except asyncio.TimeoutError as e:
                last_error = e
                MultiRPCLogger.warning(f"Can't acquire chain id from this RPC {provider.provider.endpoint_uri}")
    raise last_error


def reduce_list_of_list(ls: List[List]) -> List[any]:
    return reduce(lambda ps, p: ps + p, ls)


@dataclass
class ChainConfigTest:
    name: str
    contract_address: str
    rpc: NestedDict
    tx_hash: str
    is_proof_authority: bool = False
    multicall_address: str = None

    def __post_init__(self):
        self.contract_address = Web3.to_checksum_address(self.contract_address)
        if self.multicall_address:
            self.multicall_address = Web3.to_checksum_address(self.multicall_address)

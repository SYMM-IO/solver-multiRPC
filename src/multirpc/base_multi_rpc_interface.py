import asyncio
import logging
import time
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from typing import List, Union, Tuple, Coroutine, Dict, Optional, TypeVar, Callable

import web3
from eth_account import Account
from eth_account.datastructures import SignedTransaction
from eth_account.signers.local import LocalAccount
from eth_typing import Address, ChecksumAddress
from multicallable.async_multicallable import AsyncCall, AsyncMulticall
from requests import ConnectionError, ReadTimeout, HTTPError
from web3 import Web3, AsyncWeb3
from web3._utils.contracts import encode_transaction_data  # noqa
from web3.contract import Contract
from web3.exceptions import TimeExhausted, TransactionNotFound, BlockNotFound
from web3.types import BlockData, BlockIdentifier, TxReceipt

from .constants import ViewPolicy
from .exceptions import (
    FailedOnAllRPCs,
    TransactionFailedStatus,
    Web3InterfaceException, TransactionValueError, GetBlockFailed, DontHaveThisRpcType, NotValidViewPolicy,
)
from .gas_estimation import GasEstimation, GasEstimationMethod
from .tx_trace import TxTrace
from .utils import TxPriority, get_span_proper_label_from_provider, get_unix_time, NestedDict, create_web3_from_rpc, \
    calculate_chain_id, reduce_list_of_list, ResultEvent

T = TypeVar("T")


class BaseMultiRpc(ABC):
    """
    This class is used to be more sure when running web3 view calls and sending transactions by using of multiple RPCs.
    """

    def __init__(
            self,
            rpc_urls: NestedDict,
            contract_address: Union[Address, ChecksumAddress, str],
            contract_abi: Dict,
            view_policy: ViewPolicy = ViewPolicy.MostUpdated,
            gas_estimation: Optional[GasEstimation] = None,
            gas_limit: int = 1_000_000,
            gas_upper_bound: int = 26_000,
            apm=None,
            enable_gas_estimation: bool = False,
            is_proof_authority: bool = False,
            log_level: logging = logging.WARN
    ):
        self.rpc_urls = rpc_urls

        self.gas_estimation = gas_estimation

        self.contract_address = Web3.to_checksum_address(contract_address)
        self.contract_abi = contract_abi
        self.apm = apm

        self.contracts: NestedDict = NestedDict({'transaction': None, 'view': None})
        self.multi_calls: NestedDict = NestedDict({'transaction': None, 'view': None})

        self.functions = type("functions", (object,), {})()

        self.view_policy = view_policy
        self.gas_limit = gas_limit
        self.gas_upper_bound = gas_upper_bound
        self.enable_gas_estimation = enable_gas_estimation
        self.providers = None
        self.address = None
        self.private_key = None
        self.chain_id = None
        self.is_proof_authority = is_proof_authority

        logging.basicConfig(level=log_level)

    def _logger_params(self, **kwargs) -> None:
        if self.apm:
            self.apm.span_label(**kwargs)
        else:
            logging.info(f'params={kwargs}')

    def set_account(self, address: Union[ChecksumAddress, str], private_key: str) -> None:
        """
        Set public key and private key for sending transactions. If these values set, there is no need to pass address,
        private_key in "call" function.
        Args:
            address: sender public_key
            private_key: sender private key
        """
        self.address = Web3.to_checksum_address(address)
        self.private_key = private_key

    async def setup(self, multicall_custom_address: str = None) -> None:
        self.providers = await create_web3_from_rpc(self.rpc_urls, self.is_proof_authority)
        self.chain_id = await calculate_chain_id(self.providers)

        if self.gas_estimation is None and self.providers.get('transaction'):
            self.gas_estimation = GasEstimation(
                self.chain_id,
                reduce_list_of_list(self.providers['transaction'].values()),
                # GasEstimationMethod.RPC,
            )

        is_rpc_provided = False
        for wb3_k, wb3_v in self.providers.items():  # type: Tuple, List[web3.AsyncWeb3]
            multi_calls = []
            contracts = []
            for wb3 in wb3_v:
                rpc_url = wb3.provider.endpoint_uri
                try:
                    mc = AsyncMulticall()
                    await mc.setup(w3=wb3, custom_address=multicall_custom_address)
                    multi_calls.append(mc)
                    contracts.append(
                        wb3.eth.contract(self.contract_address, abi=self.contract_abi)
                    )
                except (ConnectionError, ReadTimeout, asyncio.TimeoutError) as e:
                    # fixme: at least we should retry not ignoring rpc
                    logging.warning(f"Ignore rpc {rpc_url} because of {e}")
                if len(multi_calls) != 0 and len(contracts) != 0:
                    is_rpc_provided = True

                self.multi_calls[wb3_k] = multi_calls
                self.contracts[wb3_k] = contracts

        if not is_rpc_provided:
            raise ValueError("No available rpc provided")

    @staticmethod
    async def __gather_tasks(execution_list: List[Coroutine], result_selector: Callable[[List], any],
                             view_policy: ViewPolicy = ViewPolicy.MostUpdated):
        """
        Get an execution list and wait for all to end. If all executable raise an exception, it will raise a
        'Web3InterfaceException' exception, otherwise returns all results which has no exception
        Args:
            execution_list:

        Returns:

        """

        def wrap_coroutine(coro: Coroutine):
            def sync_wrapper():
                try:
                    res = asyncio.run(coro)
                    return res, None
                except Exception as e:
                    return None, e

            return sync_wrapper

        if view_policy == view_policy.MostUpdated:  # wait for all task to be completed
            results = []
            exceptions = []
            with ThreadPoolExecutor() as executor:
                wrapped_coroutines = [wrap_coroutine(coro) for coro in execution_list]
                for result, exception in executor.map(lambda f: f(), wrapped_coroutines):
                    if exception:
                        exceptions.append(exception)
                    else:
                        results.append(result)

            if len(results) == 0:
                for exc in exceptions:
                    logging.exception(exc)
                raise FailedOnAllRPCs(f"All of RPCs raise exception. first exception: {exceptions[0]}")
            return result_selector(results)
        elif view_policy == view_policy.FirstSuccess:  # wait to at least 1 task completed
            return result_selector([await BaseMultiRpc.__execute_batch_tasks(
                execution_list,
                [HTTPError, ConnectionError, ValueError],
                FailedOnAllRPCs
            )])

        raise NotValidViewPolicy()

    async def _call_view_function(self,
                                  func_name: str,
                                  block_identifier: Union[str, int] = 'latest',
                                  *args, **kwargs):
        """
        Calling view function 'func_name' by using of multicall

        Args:
            func_name: view function name
            *args:
            **kwargs:

        Returns:
            the results of multicallable object for each rpc
        """

        def max_block_finder(results: List):
            max_block_number = results[0][0]
            max_index = 0
            for i, result in enumerate(results):
                if result[0] > max_block_number:
                    max_block_number = result[0]
                    max_index = i
            return results[max_index][2][0]

        for contracts, multi_calls in zip(self.contracts['view'].values(),
                                          self.multi_calls['view'].values()):  # type: any, List[AsyncMulticall]
            rpc_bracket = list(map(lambda c: c.w3.provider.endpoint_uri, contracts))

            calls = [AsyncCall(cont, func_name, args, kwargs) for cont in contracts]
            execution_list = [mc.call([call], block_identifier=block_identifier) for mc, call in
                              zip(multi_calls, calls)]
            try:
                return await self.__gather_tasks(execution_list, max_block_finder, view_policy=self.view_policy)
            except (Web3InterfaceException, asyncio.TimeoutError):
                logging.info(f"Can't call view function from this list of rpc({rpc_bracket})")
        raise Web3InterfaceException("All of RPCs raise exception.")

    async def _get_nonce(self, address: Union[Address, ChecksumAddress, str]) -> int:
        address = Web3.to_checksum_address(address)
        providers_4_nonce = self.providers.get('view') or self.providers['transaction']
        for providers in providers_4_nonce.values():
            execution_list = [
                prov.eth.get_transaction_count(address) for prov in providers
            ]
            try:
                return await self.__gather_tasks(execution_list, max)
            except (Web3InterfaceException, asyncio.TimeoutError) as e:
                logging.warning(f"get_nounce: {e}")
                pass
        raise Web3InterfaceException("All of RPCs raise exception.")

    async def _get_tx_params(
            self, nonce: int, address: str, gas_limit: int, gas_upper_bound: int, priority:
            TxPriority, gas_estimation_method: GasEstimationMethod) -> Dict:
        gas_params = await self.gas_estimation.get_gas_price(gas_upper_bound, priority, gas_estimation_method)
        tx_params = {
            "from": address,
            "nonce": nonce,
            "gas": gas_limit or self.gas_limit,
            "chainId": self.chain_id,
        }
        tx_params.update(gas_params)
        return tx_params

    @staticmethod
    async def _build_transaction(contract: Contract, func_name: str, func_args: Tuple,
                                 func_kwargs: Dict, tx_params: Dict):
        func_args = func_args or []
        func_kwargs = func_kwargs or {}
        return await contract.functions.__getattribute__(func_name)(*func_args, **func_kwargs
                                                                    ).build_transaction(tx_params)

    async def _build_and_sign_transaction(
            self, contract: Contract, provider: AsyncWeb3, func_name: str, func_args: Tuple,
            func_kwargs: Dict, signer_private_key: str, tx_params: Dict,
            enable_gas_estimation: bool) -> SignedTransaction:
        try:
            tx = await self._build_transaction(contract, func_name, func_args, func_kwargs, tx_params)
            account: LocalAccount = Account.from_key(signer_private_key)
            if enable_gas_estimation:
                estimate_gas = await provider.eth.estimate_gas(tx)
                logging.info(f"gas_estimation({estimate_gas} gas needed) is successful")
            return account.sign_transaction(tx)
        except Exception as e:
            logging.error("exception in build and sign transaction: %s, %s", e.__class__.__name__, str(e))
            raise

    async def _send_transaction(self, provider: web3.AsyncWeb3, raw_transaction: any) -> Tuple[AsyncWeb3, any]:
        rpc_url = provider.provider.endpoint_uri
        try:
            rpc_label_prefix = get_span_proper_label_from_provider(rpc_url)
            transaction = await provider.eth.send_raw_transaction(raw_transaction)
            self._logger_params(**{f"{rpc_label_prefix}_post_send_time": get_unix_time()})
            self._logger_params(tx_send_time=int(time.time() * 1000))
            return provider, transaction
        except ValueError as e:
            logging.error(f"RPC({rpc_url}) value error: {str(e)}")
            t_bnb_flag = "transaction would cause overdraft" in str(e).lower() and (await provider.eth.chain_id) == 97
            if not (
                    t_bnb_flag or
                    'nonce too low' in str(e).lower() or
                    'already known' in str(e).lower() or
                    'transaction underpriced' in str(e).lower() or
                    'account suspended' in str(e).lower() or
                    'exceeds the configured cap' in str(e).lower()
            ):
                logging.exception("_send_transaction_exception")
            raise
        except (ConnectionError, ReadTimeout, HTTPError) as e:  # FIXME complete list
            logging.debug(f"network exception in send transaction: {e.__class__.__name__}, {str(e)}")
            raise
        except Exception as e:
            # FIXME needs better exception handling
            logging.error(f"exception in send transaction: {e.__class__.__name__}, {str(e)}")
            raise

    def _handle_tx_trace(self, trace: TxTrace, func_name: str, func_args: Tuple, func_kwargs: Dict):
        """
        You can override this method to customize handling failed transaction.

        example:
            if "out of gas" in trace.text():
                raise InsufficientGasBalance(f'out of gas in {func_name}')
            if "PartyBFacet: Will be liquidatable" in trace.text():
                raise PartyBWillBeLiquidatable(f'partyB will be liquidatable in {func_name}')
            if "LibMuon: TSS not verified" in trace.text():
                raise TssNotVerified(Web3.to_hex(tx), func_name, func_args, func_kwargs, trace)
            if trace.ok():
                logging.error(f'TraceTransaction({func_name}): {trace.result().long_error()}')
                apm.capture_message(param_message={
                    'message': f'tr failed ({func_name}, {trace.result().first_usable_error()}): %s',
                    'params': (trace.text(),),
                })
        """

        pass

    async def _wait_and_get_tx_receipt(self, provider: AsyncWeb3, tx, timeout: float, func_name: str,
                                       func_args: Tuple, func_kwargs: Dict) -> Tuple[AsyncWeb3, TxReceipt]:
        con_err_count = tx_err_count = 0
        rpc_url = provider.provider.endpoint_uri
        while True:
            try:
                self._logger_params(received_provider=rpc_url)
                if (tx_receipt := await provider.eth.wait_for_transaction_receipt(tx, timeout=timeout)).status != 1:
                    trace = TxTrace(Web3.to_hex(tx))
                    self._handle_tx_trace(trace, func_name, func_args, func_kwargs)
                    raise TransactionFailedStatus(Web3.to_hex(tx), func_name, func_args, func_kwargs, trace)
                return provider, tx_receipt
            except ConnectionError:
                if con_err_count >= 5:
                    raise
                con_err_count += 1
                sleep(5)
            except (TimeExhausted, TransactionNotFound):
                if tx_err_count >= 1:  # double-check the endpoint_uri
                    raise
                tx_err_count += 1
                timeout *= 2

    @staticmethod
    async def __execute_batch_tasks(
            execution_list: List[Coroutine[None, None, T]],
            exception_handler: Optional[List[type[BaseException]]] = None,
            final_exception: Optional[type[BaseException]] = None
    ) -> T:

        async def exec_task(task: Coroutine, cancel_event: ResultEvent, lock: asyncio.Lock):
            res = await task
            async with lock:
                cancel_event.set_result(res)
            cancel_event.set()

        cancel_event = ResultEvent()
        lock = asyncio.Lock()

        tasks = [
            asyncio.create_task(exec_task(task, cancel_event, lock))
            for task in execution_list
        ]
        not_completed_tasks = tasks.copy()
        exception = None
        terminal_exception = None

        while len(not_completed_tasks) > 0:
            dones, not_completed_tasks = await asyncio.wait(
                not_completed_tasks, return_when=asyncio.FIRST_COMPLETED
            )

            for task in list(dones):
                e = task.exception()
                if e:
                    if exception_handler and isinstance(e, tuple(exception_handler)):
                        exception = e
                    else:
                        terminal_exception = e
                    continue
                if cancel_event.is_set():
                    break

            if cancel_event.is_set() or terminal_exception:
                break

        # Cancel the remaining tasks
        for task in not_completed_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        if cancel_event.is_set():
            return cancel_event.get_result()
        if terminal_exception or exception:
            raise terminal_exception or exception
        raise final_exception or RuntimeError("Execution completed without setting a result or exception.")

    async def __call_tx(
            self,
            func_name: str,
            func_args: Tuple,
            func_kwargs: Dict,
            private_key: str,
            wait_for_receipt: int,
            providers: List[AsyncWeb3],
            contracts: List[Contract],
            tx_params: Dict,
            enable_gas_estimation: bool,
    ) -> Union[str, TxReceipt]:
        signed_transaction = await self._build_and_sign_transaction(
            contracts[0], providers[0], func_name, func_args, func_kwargs, private_key, tx_params, enable_gas_estimation
        )
        tx_hash = Web3.to_hex(signed_transaction.hash)
        self._logger_params(tx_hash=tx_hash)

        execution_tx_list = [
            self._send_transaction(p, signed_transaction.raw_transaction) for p in providers
        ]
        result = await self.__execute_batch_tasks(
            execution_tx_list,
            [TransactionValueError, ValueError, ConnectionError, ReadTimeout, HTTPError],
            FailedOnAllRPCs
        )
        provider, tx = result

        logging.info(f"success tx: {provider= }, {tx= }")
        rpc_url = provider.provider.endpoint_uri
        self._logger_params(sent_provider=rpc_url)

        if not wait_for_receipt:
            return tx_hash
        execution_receipt_list = [
            self._wait_and_get_tx_receipt(p, tx, wait_for_receipt, func_name, func_args, func_kwargs) for p in providers
        ]
        provider, tx_receipt = await self.__execute_batch_tasks(
            execution_receipt_list,
            [TimeExhausted, TransactionNotFound, ConnectionError],
        )

        return tx_receipt

    async def _call_tx_function(self, address: str, gas_limit: int, gas_upper_bound: int, priority: TxPriority,
                                gas_estimation_method: GasEstimationMethod,
                                enable_gas_estimation: Optional[bool] = None, **kwargs):
        nonce = await self._get_nonce(address)
        tx_params = await self._get_tx_params(
            nonce, address, gas_limit, gas_upper_bound, priority, gas_estimation_method
        )
        enable_gas_estimation = self.enable_gas_estimation if enable_gas_estimation is None else enable_gas_estimation
        for p, c in zip(
                self.providers['transaction'].values(), self.contracts['transaction'].values()
        ):  # type: List[AsyncWeb3], List[Contract]
            try:
                return await self.__call_tx(**kwargs, providers=p, contracts=c, tx_params=tx_params,
                                            enable_gas_estimation=enable_gas_estimation)
            except (TransactionFailedStatus, TransactionValueError):
                raise
            except (ConnectionError, ReadTimeout, TimeExhausted, TransactionNotFound, FailedOnAllRPCs):
                pass
            except Exception:
                raise
        raise Web3InterfaceException("All of RPCs raise exception.")

    def check_for_view(self):
        if self.providers.get('view') is None:
            raise DontHaveThisRpcType(f"Doesn't have view RPCs")

    async def get_tx_receipt(self, tx_hash) -> TxReceipt:
        self.check_for_view()

        exceptions = (HTTPError, ConnectionError, ReadTimeout, ValueError, TimeExhausted, TransactionNotFound)

        last_exception = None
        for provider in self.providers['view'].values():  # type: List[AsyncWeb3]
            execution_tx_list = [p.eth.wait_for_transaction_receipt(tx_hash) for p in provider]
            try:
                return await self.__execute_batch_tasks(
                    execution_tx_list,
                    list(exceptions),
                    TransactionFailedStatus
                )
            except exceptions as e:
                last_exception = e
                pass
            except TransactionFailedStatus:
                raise
        raise last_exception

    async def get_block(self, block_identifier: BlockIdentifier, full_transactions: bool = False) -> BlockData:
        self.check_for_view()

        exceptions = (HTTPError, ConnectionError, ReadTimeout, ValueError, TimeExhausted, BlockNotFound)
        last_exception = None
        for provider in self.providers['view'].values():  # type: List[AsyncWeb3]
            execution_tx_params_list = [p.eth.get_block(block_identifier, full_transactions) for p in provider]
            try:
                return await self.__execute_batch_tasks(
                    execution_tx_params_list,
                    list(exceptions),
                    GetBlockFailed
                )
            except exceptions as e:
                last_exception = e
                pass
            except GetBlockFailed:
                raise
        raise last_exception

    async def get_block_number(self) -> int:
        self.check_for_view()

        exceptions = (HTTPError, ConnectionError, ReadTimeout, ValueError, TimeExhausted)
        last_exception = None
        for provider in self.providers['view'].values():  # type: List[AsyncWeb3]
            execution_tx_params_list = [asyncio.to_thread(p.eth.get_block_number) for p in provider]
            try:
                result = await self.__execute_batch_tasks(
                    execution_tx_params_list,
                    list(exceptions),
                    GetBlockFailed
                )
                return await result
            except exceptions as e:
                last_exception = e
                pass
            except GetBlockFailed:
                raise
        raise last_exception


class BaseContractFunction:
    def __init__(self, name: str, abi: Dict, multi_rpc_web3: BaseMultiRpc, typ: str):
        self.name = name
        self.mr = multi_rpc_web3
        self.typ = typ
        self.abi = abi
        self.args = None
        self.kwargs = None

    def get_encoded_data(self):
        return encode_transaction_data(
            self.mr.providers[0],
            self.name,
            self.mr.contract_abi,
            self.abi,
            self.args,
            self.kwargs,
        )

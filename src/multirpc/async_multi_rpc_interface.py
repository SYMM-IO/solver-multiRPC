import logging
from typing import Union, Dict, Optional, List

from eth_typing import Address, ChecksumAddress
from web3._utils.contracts import encode_transaction_data  # noqa
from web3.types import BlockData, BlockIdentifier, TxReceipt

from . import BaseMultiRpc
from .base_multi_rpc_interface import BaseContractFunction
from .constants import ViewPolicy
from .exceptions import DontHaveThisRpcType
from .gas_estimation import GasEstimation, GasEstimationMethod
from .utils import TxPriority, NestedDict, ContractFunctionType

logging.basicConfig(level=logging.INFO)


class AsyncMultiRpc(BaseMultiRpc):
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
    ):
        super().__init__(rpc_urls, contract_address, contract_abi, view_policy, gas_estimation, gas_limit,
                         gas_upper_bound, apm, enable_gas_estimation, is_proof_authority)

        for func_abi in self.contract_abi:
            if func_abi.get("stateMutability") in ("view", "pure"):
                function_type = ContractFunctionType.View
            elif func_abi.get("type") == "function":
                function_type = ContractFunctionType.Transaction
            else:
                continue
            self.functions.__setattr__(
                func_abi["name"],
                self.ContractFunction(func_abi["name"], func_abi, self, function_type),
            )

    async def get_nonce(self, address: Union[Address, ChecksumAddress, str]) -> int:
        return await super()._get_nonce(address)

    async def get_tx_receipt(self, tx_hash) -> TxReceipt:
        return await super().get_tx_receipt(tx_hash)

    async def get_block(self, block_identifier: BlockIdentifier, full_transactions: bool = False) -> BlockData:
        return await super().get_block(block_identifier, full_transactions)

    async def get_block_number(self) -> List[int]:
        return await super().get_block_number()

    class ContractFunction(BaseContractFunction):
        def __call__(self, *args, **kwargs):
            cf = AsyncMultiRpc.ContractFunction(self.name, self.abi, self.mr, self.typ)
            cf.args = args
            cf.kwargs = kwargs
            return cf

        async def call(
                self,
                address: str = None,
                private_key: str = None,
                gas_limit: int = None,
                gas_upper_bound: int = None,
                wait_for_receipt: int = 90,
                priority: TxPriority = TxPriority.Low,
                gas_estimation_method: GasEstimationMethod = None,
                block_identifier: Union[str, int] = 'latest',
                enable_gas_estimation: Optional[bool] = None,
        ):
            if self.mr.providers.get(self.typ) is None:
                raise DontHaveThisRpcType(f"Doesn't have {self.typ} RPCs")
            if self.typ == ContractFunctionType.View:
                return await self.mr._call_view_function(
                    self.name, block_identifier, *self.args, **self.kwargs,
                )
            elif self.typ == ContractFunctionType.Transaction:
                return await self.mr._call_tx_function(
                    func_name=self.name,
                    func_args=self.args,
                    func_kwargs=self.kwargs,
                    address=address or self.mr.address,
                    private_key=private_key or self.mr.private_key,
                    gas_limit=gas_limit or self.mr.gas_limit,
                    gas_upper_bound=gas_upper_bound or self.mr.gas_upper_bound,
                    wait_for_receipt=wait_for_receipt,
                    priority=priority,
                    gas_estimation_method=gas_estimation_method,
                    enable_gas_estimation=enable_gas_estimation
                )

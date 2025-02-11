import logging
from _decimal import Decimal
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Union

import requests
from aiohttp import ClientResponseError
from requests import ConnectionError, JSONDecodeError, ReadTimeout, RequestException
from web3 import AsyncWeb3, Web3
from web3.types import Wei

from .constants import ChainIdToGas, DEFAULT_API_PROVIDER, DevEnv, FixedValueGas, GasEstimationLogger, \
    GasEstimationMethod, \
    GasFromRpcChainIds, GasMultiplierHigh, GasMultiplierLow, GasMultiplierMedium, RequestTimeout
from .exceptions import FailedToGetGasFromApi, FailedToGetGasPrice, OutOfRangeTransactionFee
from .utils import TxPriority


class GasEstimation:

    def __init__(
            self,
            chain_id: int,
            providers: List[AsyncWeb3],
            default_method: Optional[GasEstimationMethod] = None,
            apm_client=None,
            gas_multiplier_low: Union[float, Decimal] = GasMultiplierLow,
            gas_multiplier_medium: Union[float, Decimal] = GasMultiplierMedium,
            gas_multiplier_high: Union[float, Decimal] = GasMultiplierHigh,
            gas_api_provider: str = DEFAULT_API_PROVIDER,
            log_level: logging = logging.WARN
    ):
        self.gas_api_provider = gas_api_provider
        self.chain_id = chain_id
        self.providers = providers
        self.default_method: GasEstimationMethod = default_method
        self.apm = apm_client
        self.multipliers = {
            TxPriority.Low: gas_multiplier_low,
            TxPriority.Medium: gas_multiplier_medium,
            TxPriority.High: gas_multiplier_high,
        }
        self.gas_estimation_method: Dict[GasEstimationMethod, Callable] = {
            GasEstimationMethod.GAS_API_PROVIDER: self._get_gas_from_api,
            GasEstimationMethod.RPC: self._get_gas_from_rpc,
            GasEstimationMethod.FIXED: self._get_fixed_value,
            GasEstimationMethod.CUSTOM: self._custom_gas_estimation,
        }
        self.method_sorted_priority = [
            GasEstimationMethod.GAS_API_PROVIDER,
            GasEstimationMethod.RPC,
            GasEstimationMethod.FIXED,
            GasEstimationMethod.CUSTOM
        ]
        GasEstimationLogger.setLevel(log_level)

    def __logger_params(self, **kwargs):
        if self.apm:
            self.apm.span_label(**kwargs)
        else:
            GasEstimationLogger.info(f'params={kwargs}')

    async def _get_gas_from_api(self, priority: TxPriority, gas_upper_bound: Union[float, Decimal]) -> Dict[str, Wei]:
        gas_provider = self.gas_api_provider.format(chain_id=self.chain_id)
        resp = None
        try:
            resp = requests.get(gas_provider, timeout=RequestTimeout)
            if resp.status_code != 200:
                raise FailedToGetGasFromApi(f'failed to get gas with {resp.status_code=} on {gas_provider=}')
            resp_json = resp.json()
            max_fee_per_gas = Decimal(resp_json[priority.value]["suggestedMaxFeePerGas"])
            max_priority_fee_per_gas = Decimal(resp_json[priority.value]["suggestedMaxPriorityFeePerGas"])
            base_fee = Decimal(resp_json[priority.value]["estimatedBaseFee"])
            self.__logger_params(
                max_fee_per_gas=max_fee_per_gas,
                max_priority_fee_per_gas=max_priority_fee_per_gas,
                gas_price_provider=gas_provider,
            )
            if max_fee_per_gas > gas_upper_bound:
                raise OutOfRangeTransactionFee(
                    f"gas price exceeded. {gas_upper_bound=} but it is {max_fee_per_gas}"
                )
            gas_params = {
                'baseFee': Web3.to_wei(base_fee, "GWei"),
                "maxFeePerGas": Web3.to_wei(max_fee_per_gas, "GWei"),
                "maxPriorityFeePerGas": Web3.to_wei(max_priority_fee_per_gas, "GWei"),
            }
            return gas_params
        except (RequestException, JSONDecodeError, KeyError) as e:
            if not DevEnv:
                GasEstimationLogger.exception(f'Failed to get gas info from api({self.chain_id=}) {resp.status_code=}')
            raise FailedToGetGasPrice(f"Failed to get gas info from api({self.chain_id=}): {e}")

    async def _get_gas_from_rpc(self, priority: TxPriority, gas_upper_bound: Union[float, Decimal]) -> Dict[str, Wei]:
        gas_price = None
        found_gas_below_upper_bound = False

        for provider in self.providers:  # type: AsyncWeb3
            rpc_url = provider.provider.endpoint_uri
            try:
                gas_price = await provider.eth.gas_price
                self.__logger_params(gas_price=str(gas_price / 1e9), gas_price_provider=rpc_url)
                if gas_price / 1e9 <= gas_upper_bound:
                    found_gas_below_upper_bound = True
                    break
            except (ConnectionError, ReadTimeout, ValueError, ConnectionResetError) as e:
                GasEstimationLogger.error(f"Failed to get gas price from {rpc_url}, {e=}")
            except ClientResponseError as e:
                if e.message.startswith("Too Many Requests"):
                    GasEstimationLogger.error(f"Failed to get gas price from {rpc_url}, {e=}")
                raise

        if gas_price is None:
            raise FailedToGetGasPrice("Non of RCP could provide gas price!")
        if not found_gas_below_upper_bound:
            raise OutOfRangeTransactionFee(
                f"gas price exceeded. {gas_upper_bound=} but it is {gas_price / 1e9}"
            )
        return {'gasPrice': Wei(int(gas_price * self.multipliers.get(priority, 1)))}

    async def _get_fixed_value(self, priority: TxPriority, gas_upper_bound: Union[float, Decimal]) -> Dict[str, Wei]:
        gas = ChainIdToGas.get(self.chain_id) or FixedValueGas
        if gas > gas_upper_bound:
            raise OutOfRangeTransactionFee(f"gas price exceeded. {gas_upper_bound=} but it is {gas}")
        return {"gasPrice": Web3.to_wei(gas * self.multipliers.get(priority, 1), "GWei")}

    async def _custom_gas_estimation(self, priority: TxPriority, gas_upper_bound: Union[float, Decimal]):
        raise NotImplemented()

    async def get_gas_price(
            self, gas_upper_bound: int, priority: TxPriority, method: GasEstimationMethod = None
    ) -> Dict[str, Wei]:
        if method := self.gas_estimation_method.get(method) or self.gas_estimation_method.get(self.default_method):
            try:
                return await method(priority, gas_upper_bound)
            except FailedToGetGasPrice as e:
                raise e
        gas_params = {}

        if DevEnv or self.chain_id in GasFromRpcChainIds:
            return await self._get_gas_from_rpc(priority, gas_upper_bound)
        for method_key in self.method_sorted_priority:
            try:
                gas_params = await self.gas_estimation_method[method_key](priority, gas_upper_bound)
                break
            except (FailedToGetGasPrice, OutOfRangeTransactionFee) as e:
                GasEstimationLogger.warning(f"This method({method_key}) failed to provide gas with this error: {e}")
                continue
        if not gas_params:
            raise FailedToGetGasPrice("All of methods failed to estimate gas")
        return gas_params

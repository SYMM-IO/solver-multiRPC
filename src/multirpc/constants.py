import enum

from logmon.cntr import Cntr

ChainIdToGas = {
    97: 10.1,  # Test BNB Network
}
GasFromRpcChainIds = [56, 8453]     # for this chain ids use rpc to estimate gas
FixedValueGas = 10
DEFAULT_API_PROVIDER = 'https://gas-api.metaswap.codefi.network/networks/{chain_id}/suggestedGasFees'
Default_RPC = 'https://fantom.publicnode.com'

mrpc_cntr = Cntr('mrpc')


class GasEstimationMethod(enum.Enum):
    GAS_API_PROVIDER = 0
    RPC = 1
    FIXED = 2
    CUSTOM = 3


MaxRPCInEachBracket = 3
RequestTimeout = 30
DevEnv = True

import enum

ChainIdToGas = {
    97: 10.1,  # Test BNB Network
}
FixedValueGas = 10
DEFAULT_API_PROVIDER = 'https://gas-api.metaswap.codefi.network/networks/{chain_id}/suggestedGasFees'


class GasEstimationMethod(enum.Enum):
    GAS_API_PROVIDER = 0
    RPC = 1
    FIXED = 2
    CUSTOM = 3


MaxRPCInEachBracket = 3

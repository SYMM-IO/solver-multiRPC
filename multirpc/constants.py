import enum
import logging

DEFAULT_API_PROVIDER = 'https://gas-api.metaswap.codefi.network/networks/{chain_id}/suggestedGasFees'


class ViewPolicy(enum.Enum):
    FirstSuccess = 0
    MostUpdated = 1


class GasEstimationMethod(enum.Enum):
    GAS_API_PROVIDER = 0
    RPC = 1
    FIXED = 2
    CUSTOM = 3


GasLimit = 1_000_000
GasUpperBound = 50_000

GasMultiplierLow = 1.1
GasMultiplierMedium = 1.3
GasMultiplierHigh = 1.5

MaxRPCInEachBracket = 3

# config
# It must be greater than 1, so we have a safe margin to ensure the transaction can be successful.
EstimateGasLimitBuffer = 1.1
ChainIdToGas = {
    97: 10.1,   # Test BNB Network
    250: 20,    # Ftm
    5000: 0.02  # Mantle
}
GasFromRpcChainIds = []  # for this chain ids use rpc to estimate gas
FixedValueGas = 30

MultiRPCLoggerName = 'Multi-RPC'
GasEstimationLoggerName = MultiRPCLoggerName + '.Gas-Estimation'

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

MultiRPCLogger = logging.getLogger(MultiRPCLoggerName)
GasEstimationLogger = logging.getLogger(GasEstimationLoggerName)

MultiRPCLogger.addHandler(console_handler)
GasEstimationLogger.addHandler(console_handler)

RequestTimeout = 30
DevEnv = True

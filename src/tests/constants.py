import json

from src.multirpc.utils import ChainConfigTest, NestedDict

# Arbitrum Configuration
ArbConfig = ChainConfigTest(
    'Arbitrum',
    '0xCFE3c06Fe982A7D16ce3826C64c5f0730054Dc95',
    NestedDict({
        "view": {
            1: ['https://1rpc.io/arb', 'https://rpc.ankr.com/arbitrum', 'https://arbitrum.drpc.org'],
        },
        "transaction": {
            1: ['https://1rpc.io/arb', 'https://rpc.ankr.com/arbitrum', 'https://arbitrum.drpc.org'],
        }
    }),
    '0xbc0f34536fdf5d2593081b112d49d714993d879032e0e9c6998afc3110b7f0ed'
)

# Polygon Configuration
PolyConfig = ChainConfigTest(
    'Polygon',
    '0xCa7DFDc4dB0F27484Cf5EEa1CdF380301Ef07Ce2',
    NestedDict({
        "view": {
            1: ['https://1rpc.io/matic', 'https://polygon-rpc.com'],
        },
        "transaction": {
            1: ['https://1rpc.io/matic', 'https://polygon-rpc.com'],
        }
    }),
    '0x4b8756bd1d32f62b2b9e3b46b80917bd3de4fd95695bad33e483293284f28678',
    is_proof_authority=True
)

# Base Configuration
BaseConfig = ChainConfigTest(
    'Base',
    '0x1d58e7F58d085c87E34b18DAe5A6D08d187cbcbe',
    NestedDict({
        "view": {
            1: ['https://base-rpc.publicnode.com', 'https://base.drpc.org'],
        },
        "transaction": {
            1: ['https://base-rpc.publicnode.com', 'https://base.drpc.org'],
        }
    }),
    '0xbd342d36d503af057cd79fd4f252b4629d6013d0748a2742dc99c9fcbe522072',
    is_proof_authority=True
)

# Mantle Configuration
MantleConfig = ChainConfigTest(
    'Mantle',
    '0x535D41D93cDc0818Ad8Eeb452B74e502A5742874',
    NestedDict({
        "view": {
            1: ['https://1rpc.io/mantle', 'https://mantle.drpc.org'],
        },
        "transaction": {
            1: ['https://1rpc.io/mantle', 'https://mantle.drpc.org'],
        }
    }),
    '0x9f33a56be9983753abebbe8fb048601a141097289d96b9844afb36e68f72ef82',
    is_proof_authority=False,
)

RPCsSupportingTxTrace = [
    'https://arbitrum.drpc.org',  # Arbitrum
    'https://polygon-rpc.com',  # Polygon
    'https://base.drpc.org',  # Base
    'https://mantle.drpc.org'  # Mantle
]

with open("tests/abi.json", "r") as f:
    abi = json.load(f)

PreviousBlock = 3

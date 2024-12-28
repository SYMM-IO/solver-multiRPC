import json

from src.multirpc.utils import ChainConfigTest, NestedDict

# Fantom Configuration
FtmConfig = ChainConfigTest(
    'Fantom',
    '0x20f40F64771c3a5aa0A5166d1261984E08Ca027B',
    NestedDict({
        "view": {
            1: ['https://1rpc.io/ftm', 'https://fantom.publicnode.com'],
            2: ['https://fantom-pokt.nodies.app'],
        },
        "transaction": {
            1: ['https://1rpc.io/ftm', 'https://fantom.publicnode.com'],
            2: ['https://fantom-pokt.nodies.app'],
        }
    }),
    '0x7bb81aba6b2ea3145034c676e89d4eb0bc2cdc423a95b8b32d50100fe18d90e5'
)

# Arbitrum Configuration
ArbConfig = ChainConfigTest(
    'Arbitrum',
    '0xF1fe944285c9DF10C839Fa4E901D9b71f71eD5D0',
    NestedDict({
        "view": {
            1: ['https://1rpc.io/arb', 'https://arb1.arbitrum.io/rpc'],
        },
        "transaction": {
            1: ['https://1rpc.io/arb', 'https://arb1.arbitrum.io/rpc'],
        }
    }),
    '0xbc0f34536fdf5d2593081b112d49d714993d879032e0e9c6998afc3110b7f0ed'
)

# Polygon Configuration
PolyConfig = ChainConfigTest(
    'Polygon',
    '0x6a8e0D6b591801bD699d32B0B0AC061ca9Ac8d0A',
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
    '0xE9a0bc5A0A2d82c1bD525970c3D08C91616A70A8',
    NestedDict({
        "view": {
            1: ['https://1rpc.io/base', 'https://mainnet.base.org'],
        },
        "transaction": {
            1: ['https://1rpc.io/base', 'https://mainnet.base.org'],
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
    'https://1rpc.io/arb', 'https://arb1.arbitrum.io/rpc',  # Arbitrum
    'https://1rpc.io/matic', 'https://polygon-rpc.com',     # Polygon
    'https://1rpc.io/base', 'https://mainnet.base.org',     # Base
    'https://1rpc.io/mantle', 'https://mantle.drpc.org'     # Mantle
]

with open("tests/abi.json", "r") as f:
    abi = json.load(f)

PreviousBlock = 3

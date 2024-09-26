from src.multirpc.utils import NestedDict
import json

ContractAddr = "0x20f40F64771c3a5aa0A5166d1261984E08Ca027B"
RPCs = NestedDict({
    "view": {
        1: ['https://1rpc.io/ftm', 'https://fantom.publicnode.com'],
        2: ['https://fantom.drpc.org'],
        3: ['https://fantom-pokt.nodies.app'],
    },
    "transaction": {
        1: ['https://1rpc.io/ftm', 'https://fantom.publicnode.com'],
        2: ['https://fantom.drpc.org'],
        3: ['https://fantom-pokt.nodies.app'],
    }
})

with open("tests/abi.json", "r") as f:
    abi = json.load(f)

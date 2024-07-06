from src.multirpc.utils import NestedDict
import json

ContractAddr = "0x20f40F64771c3a5aa0A5166d1261984E08Ca027B"
RPCs = NestedDict({
    "view": {
        1: ['https://1rpc.io/ftm', 'https://rpcapi.fantom.network', 'https://fantom.publicnode.com'],
        2: ['https://rpc.ftm.tools', 'https://rpc2.fantom.network', ],
        3: ['https://rpc.ankr.com/fantom'],
    },
    "transaction": {
        1: ['https://1rpc.io/ftm', 'https://rpcapi.fantom.network', 'https://fantom.publicnode.com'],
        2: ['https://rpc.ftm.tools', 'https://rpc2.fantom.network', ],
        3: ['https://rpc.ankr.com/fantom'],
    }
})

with open("tests/abi.json", "r") as f:
    abi = json.load(f)

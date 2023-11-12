# solver-MultiRpc: Reliable Ethereum Interactions with Multiple RPCs

`solver-MultiRpc` is a Python package designed to enhance the reliability of Ethereum smart contract interactions by utilizing multiple RPC (Remote Procedure Call) endpoints. If one RPC fails, the system can fall back to another, ensuring a higher success rate for your operations.

## Features

- **Multiple RPC Support**: Seamlessly switch between different RPCs to ensure uninterrupted interactions.
- **Gas Management**: Fetch gas prices from multiple sources to ensure transactions are sent with an appropriate fee.
- **Robust Error Handling**: Designed to handle failures gracefully, increasing the reliability of your applications.
- **Easy-to-use API**: Interact with Ethereum smart contracts using a simple and intuitive API.

## Installation

Install `solver-MultiRpc` using pip:

```bash
pip install solver-multiRPC
```

## Quick Start

Here's a quick example to get you started:

```python
import asyncio
import json
from multirpc import MultiRpc
from src.multirpc.utils import NestedDict


async def main():
    rpcs = NestedDict({
        "view": {
            1: ['https://1rpc.io/ftm', 'https://rpcapi.fantom.network', 'https://rpc3.fantom.network'],
            2: ['https://rpc.fantom.network', 'https://rpc2.fantom.network', ],
            3: ['https://rpc.ankr.com/fantom'],
        },
        "transaction": {
            1: ['https://1rpc.io/ftm', 'https://rpcapi.fantom.network', 'https://rpc3.fantom.network'],
            2: ['https://rpc.fantom.network', 'https://rpc2.fantom.network', ],
            3: ['https://rpc.ankr.com/fantom'],
        }
    })
    with open("abi.json", "r") as f:
        abi = json.load(f)
    multi_rpc = MultiRpc(rpcs, 'YOUR_CONTRACT_ADDRESS', contract_abi=abi, enable_gas_estimation=True)

    await multi_rpc.setup()
    multi_rpc.set_account("YOUR_PUBLIC_ADDRESS", "YOUR_PRIVATE_KEY")
    result = await multi_rpc.functions.YOUR_FUNCTION().call()
    print(result)

asyncio.run(main())
```

Replace placeholders like `YOUR_CONTRACT_ADDRESS`, `YOUR_PUBLIC_ADDRESS`, `YOUR_PRIVATE_KEY`, and `YOUR_FUNCTION` with appropriate values.

## Documentation

### Initialization

Initialize the `MultiRpc` class with your RPC URLs, contract address, and contract ABI:

```python
multi_rpc = MultiRpc(rpcs, contract_address='YOUR_CONTRACT_ADDRESS', contract_abi=abi)
```

### Setup

Before making any calls, set up the connection to the provided RPCs:

```python
await multi_rpc.setup()
```

### Setting Account

Set the Ethereum account details (address and private key) for sending transactions:

```python
multi_rpc.set_account("YOUR_PUBLIC_ADDRESS", "YOUR_PRIVATE_KEY")
```

### Calling Contract Functions

Call a function from your contract:

```python
result = await multi_rpc.functions.YOUR_FUNCTION().call()
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on our GitHub repository.

# solver-MultiRpc: Reliable Ethereum Interactions with Multiple RPCs

`solver-MultiRpc` is a robust library designed to interact with Ethereum smart contracts
using multiple RPC endpoints. This ensures reliability and availability
by distributing the load across various endpoints and retrying operations on failure.
The library provides both asynchronous (`AsyncMultiRpc`) and
synchronous (`MultiRpc`) interfaces to suit different use cases.

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

### Asynchronous Usage

Below is an example of how to use the AsyncMultiRpc class for asynchronous operations:

```python
import asyncio
import json
from src.multirpc.utils import NestedDict
from multirpc import AsyncMultiRpc


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
    multi_rpc = AsyncMultiRpc(rpcs, 'YOUR_CONTRACT_ADDRESS', contract_abi=abi, enable_gas_estimation=True)
    multi_rpc.set_account("YOUR_PUBLIC_ADDRESS", "YOUR_PRIVATE_KEY")

    result = await multi_rpc.functions.YOUR_FUNCTION().call()
    print(result)


asyncio.run(main())
```

### Synchronous Usage

Below is an example of how to use the MultiRpc class for synchronous operations:

```python
from multirpc import MultiRpc


def main():
    multi_rpc = MultiRpc(rpcs, 'YOUR_CONTRACT_ADDRESS', contract_abi=abi, enable_gas_estimation=True)
    multi_rpc.set_account("YOUR_PUBLIC_ADDRESS", "YOUR_PRIVATE_KEY")

    result = multi_rpc.functions.YOUR_FUNCTION().call()
    print(result)


main()
```

Replace placeholders like `YOUR_CONTRACT_ADDRESS`, `YOUR_PUBLIC_ADDRESS`, `YOUR_PRIVATE_KEY`, and `YOUR_FUNCTION` with
appropriate values.

## Documentation

### Initialization

Initialize the `MultiRpc` class with your RPC URLs, contract address, and contract ABI:

```python
multi_rpc = MultiRpc(rpcs, contract_address='YOUR_CONTRACT_ADDRESS', contract_abi=abi)
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
By default we return tx_receipt(wait for 90 second).
if you don't want to return tx_receipt, pass `wait_for_receipt=0` to `call()` 

### Calling Contract with another Private Key

You can call a transaction function with a different private key by passing the
`private_key`, `address` parameter to the `call()` method. Here’s an example:

```python
result = await multi_rpc.functions.YOUR_FUNCTION().call(address=PublicKey, private_key=PrivateKey)
```

### Using Block Identifier in Calls

You can specify a block identifier when calling view functions to get the state of the
contract at a specific block. Here's an example:

_Note that the majority of free RPCs only support querying blocks up to 10 minutes earlier._

```python
# You can use 'latest', 'earliest', or a specific block number
result = multi_rpc.functions.yourViewFunction().call(block_identifier='latest')  
```

### Passing View Policy

You can specify a view policy to determine how view function calls are handled.
The available view policies are `MostUpdated` and `FirstSuccess`. Here’s an example:

```python
multi_rpc = MultiRpc(rpc_urls, contract_address, contract_abi, view_policy=ViewPolicy.FirstSuccess)
```

### Passing Gas Estimation to MultiRpc

You can pass a `GasEstimation` object to the `MultiRpc` or `AsyncMultiRpc` class
to configure how gas prices are estimated. Here is an example of how to do this:

```python
from multirpc import MultiRpc, GasEstimation, GasEstimationMethod

gas_estimation = GasEstimation(
    chain_id=1,  # Mainnet
    providers=[],  # List of AsyncWeb3 providers
    default_method=GasEstimationMethod.GAS_API_PROVIDER,
    gas_api_provider='https://gasstation-mainnet.matic.network'  # Replace with your API provider
)

# Pass the GasEstimation object to MultiRpc
multi_rpc = MultiRpc(rpc_urls, contract_address, contract_abi, gas_estimation=gas_estimation)
```

The `GasEstimation` class allows you to implement a custom gas estimation method.
You need to extend the `GasEstimation` class and override the _`custom_gas_estimation` method with your custom logic.
Here is an example:

```python
from multirpc import GasEstimation, TxPriority, GasEstimationMethod
from web3 import Web3
from web3.types import Wei


class CustomGasEstimation(GasEstimation):

    async def _custom_gas_estimation(self, priority: TxPriority, gas_upper_bound: float) -> dict:
        # Your custom gas estimation logic here
        custom_gas_price = 50  # Replace with your custom logic
        if custom_gas_price > gas_upper_bound:
            raise OutOfRangeTransactionFee(f"Custom gas price {custom_gas_price} exceeds upper bound {gas_upper_bound}")
        return {
            "gasPrice": Web3.to_wei(custom_gas_price, 'gwei')
        }


# Create an instance of your custom gas estimation
custom_gas_estimation = CustomGasEstimation(
    chain_id=1,
    providers=[],
    default_method=GasEstimationMethod.CUSTOM,
    gas_api_provider=''
)

# Use it with MultiRpc
multi_rpc = MultiRpc(rpc_urls, contract_address, contract_abi, gas_estimation=custom_gas_estimation)
```

You can specify which gas estimation method in `call()` method. Here's an example:

```python
tx_hash = multi_rpc.functions.yourTransactionFunction().call(
    gas_estimation_method=GasEstimationMethod.RPC,  # Specify the gas estimation method
)
```

By default, we check all possible ways(api, rpc, fixed, custom) to get `gasPrice`.
but, if you pass method we only use passed method

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on our GitHub repository.

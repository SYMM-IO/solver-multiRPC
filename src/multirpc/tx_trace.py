import logging

import requests

from .constants import Default_RPC as RPC


class TxTrace:
    """
    geth trace transaction sample output :

    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "from": "0x15d34aaf54267db7d7c367839aaf71a00a2c6a65",
        "gas": "0x989680",
        "gasUsed": "0xca4b",
        "to": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0",
        "input": "0x3f65c7f4000000000000000000000000ba55e57bb198a641135e9dc9e96ebff834cab11000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000160000000000000000000000000000000000000000000000000000000006590012200000000000000000000000000000000000000000000000000000000000001a0ffffffffffffffffffffffffffffffffffffffffffffffffe440925e7ed57800ffffffffffffffffffffffffffffffffffffffffffffffffe440925e7ed5780000000000000000000000000000000000000000000000000000000000000001e000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000220891d24df965ef1367f4c8d974f394b0a43f7be3a2767ba887cef8dd2adfd89c000000000000000000000000090f79bf6eb2c4f870365e785982e1f101e93b906000000000000000000000000392118fc9f5acf2b2b9e509804bb7e68253635b80000000000000000000000000000000000000000000000000000000000000020ad0a18a3d1d4340dcc24a08636a2782e2edf6d8e5434939763ebf402b166d7e40000000000000000000000000000000000000000000000000000000000000020b01bc3cb7585f01e38c0af92705ce6799b89ab1cd49955757b4094468941f8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000417de46c7e53aa9365ab17de1e6f3efedd87d67fd77b341d3f4bd5919cd19805ae2a28c3b17771caf6e661db72e6f684cc6caba3e40e1436d591e98e0f1e73ec2b1b00000000000000000000000000000000000000000000000000000000000000",
        "output": "0x08c379a0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000234c69717569646174696f6e46616365743a2050617274794120697320736f6c76656e740000000000000000000000000000000000000000000000000000000000",
        "error": "execution reverted",
        "revertReason": "LiquidationFacet: PartyA is solvent",
        "calls": [
          {
            "from": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0",
            "gas": "0x95b6b0",
            "gasUsed": "0x4aa7",
            "to": "0xa513e6e4b8f2a923d98304ec87f64353c4d5c853",
            "input": "0x3f65c7f4000000000000000000000000ba55e57bb198a641135e9dc9e96ebff834cab11000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000160000000000000000000000000000000000000000000000000000000006590012200000000000000000000000000000000000000000000000000000000000001a0ffffffffffffffffffffffffffffffffffffffffffffffffe440925e7ed57800ffffffffffffffffffffffffffffffffffffffffffffffffe440925e7ed5780000000000000000000000000000000000000000000000000000000000000001e000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000220891d24df965ef1367f4c8d974f394b0a43f7be3a2767ba887cef8dd2adfd89c000000000000000000000000090f79bf6eb2c4f870365e785982e1f101e93b906000000000000000000000000392118fc9f5acf2b2b9e509804bb7e68253635b80000000000000000000000000000000000000000000000000000000000000020ad0a18a3d1d4340dcc24a08636a2782e2edf6d8e5434939763ebf402b166d7e40000000000000000000000000000000000000000000000000000000000000020b01bc3cb7585f01e38c0af92705ce6799b89ab1cd49955757b4094468941f8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000417de46c7e53aa9365ab17de1e6f3efedd87d67fd77b341d3f4bd5919cd19805ae2a28c3b17771caf6e661db72e6f684cc6caba3e40e1436d591e98e0f1e73ec2b1b00000000000000000000000000000000000000000000000000000000000000",
            "output": "0x08c379a0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000234c69717569646174696f6e46616365743a2050617274794120697320736f6c76656e740000000000000000000000000000000000000000000000000000000000",
            "error": "execution reverted",
            "revertReason": "LiquidationFacet: PartyA is solvent",
            "value": "0x0",
            "type": "DELEGATECALL"
          }
        ],
        "value": "0x0",
        "type": "CALL"
      }
    }
    """

    def __init__(self, tx_hash):
        self.tx_hash = tx_hash
        self.response = self.tx_trace()
        self._json = None

    def tx_trace(self):
        try:
            data = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "debug_traceTransaction",
                "params": [
                    self.tx_hash,
                    {"tracer": 'callTracer', "disableStack": False, "disableStorage": True}
                ]
            }

            response = requests.post(RPC, json=data)
            if response.status_code == 200:
                return response
            logging.error(f'tx_trace status = {response.status_code}')
        except requests.HTTPError:
            logging.exception('Exception in debug_traceTransaction')

    def ok(self):
        return bool(self.response)

    def text(self):
        if self.ok():
            return self.response.text
        return ''

    def json(self) -> dict:
        if self._json:
            return self._json
        if self.ok():
            self._json = self.response.json()
        else:
            self._json = {}
        return self._json

    def result(self):
        return TxTraceResult(result=self.json().get('result', {}))


class TxTraceResult:

    def __init__(self, result):
        self._json = result

    def get(self, key, default=None):
        return self._json.get(key, default)

    def error(self):
        return self.get('error')

    def revert_reason(self):
        return self.get('revertReason')

    def from_(self):
        return self.get('from')

    def to(self):
        return self.get('to')

    def gas_used(self):
        return self.get('gasUsed')

    def calls(self) -> list['TxTraceResult']:
        return [TxTraceResult(result=call) for call in self.get('calls', [])]

    def all_revert_reasons(self) -> list:
        revert_reasons = []

        if current_reason := self.get('revertReason'):
            revert_reasons.append(current_reason)

        if calls := self.calls():
            for child_call in calls:
                revert_reasons += child_call.all_revert_reasons()

        return revert_reasons

    def short_error(self):
        return f'error={self.error()} revertReason={self.revert_reason()}'

    def long_error(self):
        revert_reasons = self.all_revert_reasons()
        return f'error={self.error()} revert-reasons={revert_reasons}'

    def first_usable_error(self):
        for error in [self.error()] + self.all_revert_reasons():
            if 'execution reverted' not in error and 'MultiAccount: Error occurred' not in error:
                return error
        return ''

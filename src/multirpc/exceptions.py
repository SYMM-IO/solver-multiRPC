BaseException_ = Exception


class Web3InterfaceException(BaseException_):
    def __str__(self):
        return f"{self.__class__.__name__}({self.args[0]})"


class OutOfRangeTransactionFee(Web3InterfaceException):
    pass


class FailedOnAllRPCs(Web3InterfaceException):
    pass


class ViewCallFailed(Web3InterfaceException):
    pass


class TransactionFailedStatus(Web3InterfaceException):
    pass


class FailedToGetGasPrice(Web3InterfaceException):
    pass


class MaximumRPCInEachBracketReached(Web3InterfaceException):
    pass


class AtLastProvideOneValidRPCInEachBracket(Web3InterfaceException):
    pass


class TransactionValueError(Web3InterfaceException):
    pass


class GetBlockFailed(Web3InterfaceException):
    pass


class DontHaveThisRpcType(Web3InterfaceException):
    pass

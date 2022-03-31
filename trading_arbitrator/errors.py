
class InvalidLoopError(Exception):

    def __init__(self, loop):
        """
        Raised when a loop fails verification
        """

        super().__init__()
        self.loop = loop

    def __str__(self):
        return "Invalid loop: {}".format(str(self.loop))


class InvalidPoolException(Exception):

    def __init__(self):
        """
        Raised when a pool cannot be initialized with provided data
        """

        super().__init__()

    def __str__(self):
        return "Invalid pool"


class LPDepletedError(Exception):

    def __init__(self):
        """
        Raised when a side of a LP is depleted.
        """
        super().__init__()


    def __str__(self):
        return "LP tokens were fully depleted!"

class ImpossibleConversionException(Exception):

    def __init__(self, data: str = ""):
        """
        Raised when a conversion is impossible
        """

        super().__init__()
        self.data = data

    def __str__(self):
        return "Invalid conversion: {}".format(str(self.data))


class WrongExTypeError(Exception):

    def __init__(self, ex_type):
        """
        Raised when an exchange type doesn't match its data
        """

        super().__init__()
        self.ex_type = ex_type

    def __str__(self):
        return "Invalid conversion: {}".format(str(self.ex_type))

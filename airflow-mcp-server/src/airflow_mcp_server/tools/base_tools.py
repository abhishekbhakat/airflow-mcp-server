from abc import ABC, abstractmethod

class BaseTools(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def run(self):
        pass
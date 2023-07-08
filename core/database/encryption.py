from abc import ABC, abstractmethod

from cryptography.fernet import Fernet, MultiFernet

__all__ = (
    'Encryption',
    'FernetEngine',
)


class Encryption(ABC):
    @abstractmethod
    def encrypt(self, value: bytes) -> bytes:
        pass

    @abstractmethod
    def decrypt(self, value: bytes) -> bytes:
        pass


class FernetEngine(Encryption):
    def __init__(self, keys: tuple[str | bytes, ...]) -> None:
        self.__keys: tuple[str | bytes, ...] = keys
        self.fernet: MultiFernet = MultiFernet([Fernet(key) for key in self.__keys])

    def add_key(self, key: str | bytes) -> None:
        self.__keys += (key,)
        self.fernet = MultiFernet([Fernet(key) for key in self.__keys])

    def rotate(self, value: bytes) -> bytes:
        return self.fernet.rotate(value)

    def encrypt(self, value: str | bytes) -> str:
        if isinstance(value, str):
            value = value.encode()
        encrypted = self.fernet.encrypt(value)
        return encrypted.decode()

    def decrypt(self, value: str | bytes) -> str:
        if isinstance(value, str):
            value = value.encode()
        decrypted = self.fernet.decrypt(value)
        return decrypted.decode()

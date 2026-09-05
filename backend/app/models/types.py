from sqlalchemy.types import Text, TypeDecorator

from app.core.crypto import decrypt_text, encrypt_text


class EncryptedText(TypeDecorator):
    """
    Tipo de dado SQLAlchemy que encripta antes de salvar no banco
    e decripta automaticamente ao ler da tabela.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return encrypt_text(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return decrypt_text(value)
        return value

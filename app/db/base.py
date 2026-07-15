from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convenção de nomes explícita para constraints, para gerar migrations Alembic
# determinísticas e nomes previsíveis em qualquer dialeto de banco.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base compartilhada por todos os modelos ORM da plataforma."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

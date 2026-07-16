from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NovoCodigo(Base):
    """Contador central de geração de chave por organização e por contador (Seção 6.1) —
    equivalente à tabela `NOVOCODIGO` do HCM de destino. Hoje hospedada no banco de staging
    da própria plataforma (ainda não há integração ao Oracle de destino — Anexo A); quando
    essa integração existir, o Key Resolution Service passa a ler/gravar a tabela real do
    HCM sem alterar sua interface pública."""

    __tablename__ = "novocodigo"

    nr_org: Mapped[int] = mapped_column(Integer, primary_key=True)
    cd_contador: Mapped[str] = mapped_column(String(100), primary_key=True)
    nr_proximo: Mapped[int] = mapped_column(Integer)

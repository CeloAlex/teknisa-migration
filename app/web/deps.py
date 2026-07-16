from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.usuario import Papel, Usuario


class NaoAutenticado(Exception):
    """Levantada quando uma rota do portal exige login e não há sessão válida — o handler
    registrado em app/main.py responde com um redirect para a tela de login."""


class SemPermissao(Exception):
    """Levantada quando o usuário logado não tem o papel exigido pela rota — o handler
    registrado em app/main.py renderiza uma página 403."""

    def __init__(self, mensagem: str = "Você não tem permissão para acessar esta página.") -> None:
        self.mensagem = mensagem
        super().__init__(mensagem)


async def usuario_logado(request: Request, db: AsyncSession = Depends(get_db)) -> Usuario | None:
    usuario_id = request.session.get("usuario_id")
    if usuario_id is None:
        return None
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        return None
    return usuario


async def exigir_login(usuario: Usuario | None = Depends(usuario_logado)) -> Usuario:
    if usuario is None:
        raise NaoAutenticado()
    return usuario


def exigir_papel(*papeis: Papel):
    """Fábrica de dependency — bloqueia quem não estiver logado com um dos papéis dados.
    Auditor nunca deve ser incluído aqui: é somente-leitura em todo o portal por regra
    geral, não papel a papel."""

    papeis_permitidos = {p.value for p in papeis}

    async def checker(usuario: Usuario = Depends(exigir_login)) -> Usuario:
        if usuario.papel not in papeis_permitidos:
            raise SemPermissao()
        return usuario

    return checker


async def existe_algum_usuario(db: AsyncSession) -> bool:
    resultado = await db.execute(select(func.count()).select_from(Usuario))
    return resultado.scalar_one() > 0

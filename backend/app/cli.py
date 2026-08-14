"""Operator CLI for account management.

Accounts are created here rather than through a public sign-up route. Run it
inside the backend container, e.g.:

    docker compose exec backend python -m app.cli create-user leo

The password is read interactively (never passed on the command line, so it
does not land in shell history or the process list).
"""

import argparse
import asyncio
import getpass
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine, get_session_factory
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import hash_password


async def _create_user(username: str, password: str) -> None:
    session_factory = get_session_factory()
    session: AsyncSession
    async with session_factory() as session:
        repository = UserRepository(session)
        if await repository.get_by_username(username) is not None:
            raise SystemExit(f"Já existe uma conta com o usuário '{username}'.")
        await repository.create(User(username=username, password_hash=hash_password(password)))
    await get_engine().dispose()


def _prompt_password() -> str:
    password = getpass.getpass("Senha: ")
    if not password:
        raise SystemExit("A senha não pode ser vazia.")
    if password != getpass.getpass("Confirme a senha: "):
        raise SystemExit("As senhas não conferem.")
    return password


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="app.cli", description="Gerencia contas do CozinIA.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-user", help="Cria uma nova conta.")
    create.add_argument("username", help="Nome de usuário para login.")

    args = parser.parse_args(argv)

    if args.command == "create-user":
        password = _prompt_password()
        asyncio.run(_create_user(args.username, password))
        print(f"Conta '{args.username}' criada.")
    else:  # pragma: no cover - argparse enforces a valid command
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""İlk yönetici hesabını parolayı terminale veya komut geçmişine yazmadan oluşturur."""

from __future__ import annotations

import argparse
import getpass

from isg_api.config import Settings
from isg_api.database import create_database_engine
from isg_api.models import AppUser, UserRole
from isg_api.security import hash_password, normalize_username
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True, help="Küçük harfli giriş adı")
    parser.add_argument("--display-name", required=True, help="Panelde görünen ad")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        username = normalize_username(args.username)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    display_name = args.display_name.strip()
    if len(display_name) < 2:
        raise SystemExit("Görünen ad en az 2 karakter olmalıdır")

    password = getpass.getpass("Yönetici parolası (en az 12 karakter): ")
    confirmation = getpass.getpass("Parolayı tekrar gir: ")
    if password != confirmation:
        raise SystemExit("Parolalar eşleşmiyor")
    try:
        password_hash = hash_password(password)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    finally:
        password = ""
        confirmation = ""

    engine = create_database_engine(Settings())
    try:
        with Session(engine) as database:
            user_count = database.scalar(select(func.count()).select_from(AppUser))
            if user_count:
                raise SystemExit(
                    "İlk kullanıcı zaten oluşturulmuş. Yeni hesapları yönetici API'sinden ekle."
                )

            database.add(
                AppUser(
                    username=username,
                    display_name=display_name,
                    password_hash=password_hash,
                    role=UserRole.ADMIN,
                )
            )
            try:
                database.commit()
            except IntegrityError as error:
                database.rollback()
                raise SystemExit("Yönetici hesabı oluşturulamadı") from error
    finally:
        engine.dispose()

    print(f"İlk yönetici oluşturuldu: {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

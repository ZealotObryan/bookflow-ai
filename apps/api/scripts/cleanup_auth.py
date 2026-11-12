from app.core.maintenance import purge_expired_auth_material
from app.db.session import get_session_factory


def main() -> None:
    with get_session_factory()() as db:
        result = purge_expired_auth_material(db)
    print(result)


if __name__ == "__main__":
    main()

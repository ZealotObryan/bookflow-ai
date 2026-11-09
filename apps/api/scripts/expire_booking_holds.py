from app.core.maintenance import expire_booking_holds
from app.db.session import get_session_factory


def main() -> None:
    with get_session_factory()() as db:
        result = expire_booking_holds(db)
    print(result)


if __name__ == "__main__":
    main()

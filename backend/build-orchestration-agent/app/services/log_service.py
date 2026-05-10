from app.db.database import SessionLocal
from app.db.models import Log


def save_log(build_id: str, message: str):
    db = SessionLocal()

    log = Log(
        build_id=build_id,
        message=message
    )

    db.add(log)
    db.commit()
    db.close()
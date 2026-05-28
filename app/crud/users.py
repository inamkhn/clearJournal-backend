from sqlalchemy.orm import Session

# Simple mock user for testing/dependency fallback
class MockUser:
    id = 1
    email = "test@example.com"
    full_name = "Test User"
    is_active = True
    is_admin = True

def get_user_by_id(db: Session, user_id: int):
    # Standard DB implementation would query SQLAlchemy model
    # db.query(User).filter(User.id == user_id).first()
    return MockUser()

from datetime import datetime, timedelta

from database import SessionLocal
from models import Conversation, Memory, Message, User


def seed_demo_data() -> None:
    """
    Seed minimal demo data for local development using ASCII-only text to avoid encoding issues.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == "demo-user").first()
        if not user:
            user = User(id="demo-user", nickname="demo-user")
            db.add(user)
            db.commit()
            db.refresh(user)

        has_conversation = db.query(Conversation).filter(Conversation.user_id == user.id).count() > 0
        if not has_conversation:
            conv1 = Conversation(
                user_id=user.id,
                title="Sales growth consultation",
                main_concern="Regular customers are declining and monthly revenue is flat.",
                channel="chat",
                started_at=datetime.utcnow() - timedelta(days=2),
            )
            conv2 = Conversation(
                user_id=user.id,
                title="Hiring and staffing",
                main_concern="Short on hall staff and hiring is not progressing.",
                channel="chat",
                started_at=datetime.utcnow() - timedelta(days=5),
            )
            db.add_all([conv1, conv2])
            db.commit()
            db.refresh(conv1)
            db.refresh(conv2)

            messages_conv1 = [
                Message(conversation_id=conv1.id, role="user", content="Sales are sluggish and regulars are decreasing."),
                Message(
                    conversation_id=conv1.id,
                    role="assistant",
                    content="Where do you feel the pain is bigger: number of visitors or average spend?",
                ),
                Message(
                    conversation_id=conv1.id,
                    role="user",
                    content="Visitor count is dropping the most. New customer acquisition is also weak.",
                ),
            ]
            messages_conv2 = [
                Message(conversation_id=conv2.id, role="user", content="We lack hall staff and hiring is not moving."),
                Message(
                    conversation_id=conv2.id,
                    role="assistant",
                    content="Let's review hiring channels and the content of your job posts.",
                ),
            ]
            db.add_all(messages_conv1 + messages_conv2)
            db.commit()

        has_memory = db.query(Memory).filter(Memory.user_id == user.id).count() > 0
        if not has_memory:
            memory = Memory(
                user_id=user.id,
                current_concerns='["Costs are rising and margins are thin", "Regular customers are decreasing"]',
                important_points='["Want to review gross margin trends", "Need ideas for local customer acquisition"]',
                remembered_facts='["Running a small restaurant in Fukuoka", "Considering a second location"]',
                last_updated_at=datetime.utcnow(),
            )
            db.add(memory)
            db.commit()
    finally:
        db.close()

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import bcrypt

# 1. إعداد الاتصال
DATABASE_URL = "sqlite:///./ultimate_storage.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. تعريف جدول المنتج
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, default="")
    category = Column(String, default="")
    supplier = Column(String, default="")
    quantity = Column(Integer, default=0)
    price = Column(Integer, default=0)
    reorder_level = Column(Integer, default=5)
    added_at = Column(DateTime, default=datetime.utcnow)

# 3. تعريف جدول المستخدمين
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)

# 4. دوال مساعدة لكلمات المرور (هنا تم إضافة الدالة المفقودة)
def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str):
    """
    هذه هي الدالة التي كانت مفقودة وتمت إضافتها.
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())

# 5. إنشاء الجداول والمستخدمين الافتراضيين
def create_db_and_users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(User).first():
        admin_user = User(username="admin", password_hash=hash_password("admin123"), role="admin")
        guest_user = User(username="user", password_hash=hash_password("user123"), role="user")
        db.add(admin_user)
        db.add(guest_user)
        db.commit()
    db.close()

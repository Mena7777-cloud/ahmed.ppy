from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import bcrypt

DATABASE_URL = "sqlite:///./system_v3_final.db" # اسم جديد لضمان بداية نظيفة
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    transactions = relationship("Transaction", back_populates="product")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String, nullable=False)
    quantity_change = Column(Integer, nullable=False)
    reason = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="transactions")
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String)
    action = Column(String, nullable=False)
    details = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)

def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_db_and_users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(User).first():
        admin_user = User(username="admin", password_hash=hash_password("admin123"), role="admin")
        guest_user = User(username="user", password_hash=hash_password("user123"), role="user")
        db.add(admin_user)
        db.add(guest_user)
        db.commit()
        log = AuditLog(username="System", action="إنشاء المستخدمين الافتراضيين")
        db.add(log)
        db.commit()
    db.close()

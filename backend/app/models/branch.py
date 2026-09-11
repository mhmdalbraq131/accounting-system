from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Branch(Base):
    __tablename__ = "branches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

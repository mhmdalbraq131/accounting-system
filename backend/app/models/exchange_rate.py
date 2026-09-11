from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), index=True)
    rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

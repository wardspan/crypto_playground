from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True)
    initial_investment = Column(Float)
    current_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    holdings = relationship("Holding", back_populates="portfolio")

    def to_dict(self):
        return {
            'id': self.id,
            'initial_investment': self.initial_investment,
            'current_value': self.current_value,
            'created_at': self.created_at.isoformat(),
            'holdings': [holding.to_dict() for holding in self.holdings]
        }

class Holding(Base):
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    coin_id = Column(String)
    amount = Column(Float)
    coins = Column(Float, default=0)
    
    portfolio = relationship("Portfolio", back_populates="holdings")

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'coin_id': self.coin_id,
            'amount': self.amount,
            'coins': self.coins
        }

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    coin_id = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)  # 'above' or 'below'
    price_threshold = Column(Float, nullable=False)
    user_email = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'coin_id': self.coin_id,
            'price': self.price,
            'timestamp': self.timestamp.isoformat()
        }

class AlertSettings(Base):
    __tablename__ = "alert_settings"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String)
    loss_threshold = Column(Float)  # Percentage loss threshold
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
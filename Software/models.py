from sqlalchemy import create_engine, ForeignKey, String, Float, Integer, Column, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class MoistureContent(Base):
    __tablename__ = "MoistureContent"
    id = Column(Integer, primary_key=True)
    moisture_percent = Column("moisture_percent", Float)
    temperature = Column("temperature", Float)
    humidity = Column("humidity", Float)
    date_created = Column(DateTime(), default=datetime.now)

    def __init__(self, moisture_percent, temperature, humidity):
        self.moisture_percent = moisture_percent
        self.temperature = temperature
        self.humidity = humidity

# Database setup function
def setup_database():
    db = "sqlite:///moistureDB.db"
    engine = create_engine(db)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
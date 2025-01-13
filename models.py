from sqlalchemy import create_engine, ForeignKey, String, Float, Integer, Column, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Moisture(Base):
    __tablename__ = "MoistureContent"
    id = Column(Integer, primary_key=True)
    moisture_percent = Column("moisture_percent", Float)
    date_created = Column(DateTime(), default=datetime.datetime.now)
    temperature = Column("temperature", Float)
    humidity = Column("humidity", Float)

    def __init__(self, moisture_percent, date_created):
        self.moisture_percent = moisture_percent
        self.date_created = date_created
        self.temperature = None  # Initialize temperature
        self.humidity = None    # Initialize humidity

db = "sqlite:///moistureDB.db"
engine = create_engine(db)
Base.metadata.create_all(bind=engine)   
Session = sessionmaker(bind=engine)
session = Session()
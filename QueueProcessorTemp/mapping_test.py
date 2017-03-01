import orm_mapping
from base import engine
from sqlalchemy.orm import sessionmaker
from orm_mapping import *

Session = sessionmaker(bind=engine)
session = Session()

for instance in session.query(Instrument).order_by(Instrument.id):
    print (instance.name, instance.is_active)

instrument = session.query(Instrument).filter_by(name='WISH').first()
print instrument.name
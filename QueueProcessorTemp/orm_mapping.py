from sqlalchemy import Column, Integer, String, Table, MetaData
from sqlalchemy.orm import relationship
from base import Base, metadata, engine

# Create all of the classes for all of the needed tables in the autoreduce schema
class Instrument(Base):
    __table__ = Table('reduction_viewer_instrument', metadata, autoload=True, autoload_with=engine)

class StatusID(Base):
    __table__ = Table('reduction_viewer_status', metadata, autoload=True, autoload_with=engine)

class ReductionRun(Base):
    __table__ = Table('reduction_viewer_reductionrun', metadata, autoload=True, autoload_with=engine)

class Experiment(Base):
    __table__ = Table('reduction_viewer_experiment', metadata, autoload=True, autoload_with=engine)
    
class InstrumentVariables(Base):
    __table__ = Table('reduction_variables_instrumentvariable', metadata, autoload=True, autoload_with=engine)

class DataLocation(Base):
    __table__ = Table('reduction_viewer_datalocation', metadata, autoload=True, autoload_with=engine)

class Notification(Base):
    __table__ = Table('reduction_viewer_notification', metadata, autoload=True, autoload_with=engine)

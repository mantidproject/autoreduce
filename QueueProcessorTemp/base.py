from sqlalchemy.ext.declarative import declarative_base
from settings import MYSQL
from sqlalchemy import create_engine, MetaData

Base = declarative_base()

# Create the connection string for SQLAlchemy
connect_string = 'mysql+mysqldb://' + MYSQL['USER'] + ':' + MYSQL['PASSWD'] + \
                 '@' + MYSQL['HOST'] + '/' + MYSQL['DB'] 

# Create the engine and the metadata which will be passed to the mapping script
# The pool_recycle will ensure that MySQL will not close this connection if it
# is idle for more than 8 hours.
engine = create_engine(connect_string, pool_recycle=3600)
metadata = MetaData(engine)


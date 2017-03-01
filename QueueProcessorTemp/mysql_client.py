import MySQLdb as mysql
from settings import MYSQL

class MySQL():
    def connect(self):
        database = mysql.connect(host=MYSQL['HOST'], user=MYSQL['USER'], 
                                 passwd=MYSQL['PASSWD'], db=MYSQL['DB'])
        return database
        
    def execute_search(self, database, query):
        cursor = database.cursor()
        cursor.execute(query)
        return ((cursor.fetchall())[0])
    
    def execute_update(self, database, query):
        cursor = database.cursor()
        cursor.execute(query)
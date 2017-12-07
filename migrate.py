from playhouse.migrate import *

my_db = SqliteDatabase('cianoid.db')
migrator = SqliteMigrator(my_db)

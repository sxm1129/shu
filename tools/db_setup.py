import mysql.connector
from mysql.connector import errorcode

config = {
  'user': 'sxm1129',
  'password': 'hs@A1b2c3d4e5',
  'host': '39.102.122.9',
  'port': 3306,
  'database': 'sxm1129', # Assuming the database name is the same as the user, or I should check if I need to create one. 
  # usually shared hosts give a db same as username. If not, I might need to connect without db and create one.
  # But the prompt said "The database is currently empty", implying a DB exists. 
  # I'll try connecting to 'sxm1129' first.
}

DB_NAME = 'sxm1129'

TABLES = {}
TABLES['books'] = (
    "CREATE TABLE `books` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `filename` varchar(255) NOT NULL,"
    "  `title` varchar(255),"
    "  `book_title` varchar(255),"
    "  `author` varchar(255),"
    "  `publication_date` varchar(50),"
    "  `copyright_year` varchar(50),"
    "  `last_modified` varchar(50),"
    "  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,"
    "  PRIMARY KEY (`id`)"
    ") ENGINE=InnoDB")

TABLES['chapters'] = (
    "CREATE TABLE `chapters` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `book_id` int(11) NOT NULL,"
    "  `book_name` varchar(255),"
    "  `chapter_index` int(11) NOT NULL,"
    "  `title` varchar(255),"
    "  `content` LONGTEXT,"
    "  `content_length` INT,"
    "  PRIMARY KEY (`id`),"
    "  FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE"
    ") ENGINE=InnoDB")

def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

try:
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_BAD_DB_ERROR:
        # Database does not exist, try to create it
        try:
            # Connect without database
            temp_config = config.copy()
            del temp_config['database']
            cnx = mysql.connector.connect(**temp_config)
            cursor = cnx.cursor()
            print(f"Creating database {DB_NAME}...")
            cursor.execute(f"CREATE DATABASE {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
            cnx.database = DB_NAME
        except mysql.connector.Error as err2:
            print(f"Failed creating database: {err2}")
            exit(1)
    else:
        print(err)
        exit(1)

def create_tables():
    cursor.execute("USE {}".format(DB_NAME))
    
    # Drop tables if they exist to ensure schema update
    cursor.execute("DROP TABLE IF EXISTS chapters")
    cursor.execute("DROP TABLE IF EXISTS books")
    
    for table_name in TABLES:
        table_description = TABLES[table_name]
        try:
            print("Creating table {}: ".format(table_name), end='')
            cursor.execute(table_description)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)
        else:
            print("OK")

create_tables()

cursor.close()
cnx.close()

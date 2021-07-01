# Might not need this
import sqlite3

def create_connection():
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect("./data/GRNBoost2.db")
        return conn
    except:
        print("SQL connectino not established")

    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        print('Table created')

    except:
        print("Table not created")

def create_query(request_id):
    table_name = 'Table_' + str(request_id)

    query = f""" CREATE TABLE IF NOT EXISTS {table_name} (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        begin_date text,
                                        end_date text
                                    ); """

    conn = create_connection()

    create_table(conn, query)

    return table_name
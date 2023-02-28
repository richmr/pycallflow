import sqlite3
import sys

CALLFLOW_TABLES = {
    "Files": """
        CREATE TABLE Files (
            fileID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            file_full_path TEXT,
            package_path TEXT,
            file_mod_time INTEGER
        ) 
    """,
    "Entities":"""
        CREATE TABLE Entities (
            entityID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            fileID INTEGER,
            entity_name TEXT,
            entity_type TEXT,
            import_path TEXT, 
            member_of_class INTEGER            
        )
    """,
    "Calls":"""
        CREATE TABLE Calls (
            callID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            entityID INTEGER, 
            called_entity_ID INTEGER,
            collision_num TEXT
        )
    """
}

class callFlowData:
    """
    Holds the discovered objects and sqlite3 connection for resuse across call flow activities    
    """
    sqlite_connection = None
    discoveredObjects = []

    def __init__(self, sqlite3_filename=":memory:") -> None:
        self.sqlite3_filename = sqlite3_filename
        pass

    def getSqliteConnection(self, checkTablesExist=True):
        if self.sqlite_connection is None:
            cnxn = sqlite3.connect(self.sqlite3_filename)
            cnxn.row_factory = sqlite3.Row
            if checkTablesExist:
                self.checkDBHasRequiredTables(cnxn)
            self.sqlite_connection = cnxn
        return self.sqlite_connection

    def checkDBHasRequiredTables(self, db_conn, createIfMissing=True):
        db_cursor = db_conn.cursor()
        tablesNeeded = list(CALLFLOW_TABLES.keys())
        listOfTables = db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        for table in listOfTables:
            try:
                tablesNeeded.remove(table[0])
            except Exception as badnews:
                # Just here to catch "table not found", we ignore these
                pass

        if not createIfMissing:
            if len(tablesNeeded) > 0:
                raise Exception(f"callflow.sqlsetup.checkDBHasRequiredTables: Missing {','.join(tablesNeeded)}.  Set createIfMissing=True to build them.", file=sys.stderr)

        # Build the remaining
        for table in tablesNeeded:
            stmt = CALLFLOW_TABLES[table]
            db_cursor.execute(stmt)
        return

    def clearTables(self, db_conn):
        db_cursor = db_conn.cursor()
        for table in CALLFLOW_TABLES:
            stmt = f"DELETE FROM {table};"
            db_cursor.execute(stmt)

    def addDiscoveredObject(self, obj):
        self.discoveredObjects.append(obj)

    def getDiscoveredObjects(self):
        return self.discoveredObjects

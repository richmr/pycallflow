import os
import pathlib

def buildFileDB(target_object, db_conn, targetIsDirectory = False):
    # Get the file list
    db_cursor = db_conn.cursor()
    search_paths = [target_object]
    if not targetIsDirectory:
        search_paths = target_object.__path__
    for search_path in search_paths:
        for root, dirs, files in os.walk(search_path, topdown=True):
            for name in files:
                if name.endswith(".py"):
                    if name == "setup.py":
                        # These files seem to cause problems with this technique
                        continue
                    file_full_path = os.path.join(root, name)
                    file_full_path = os.path.normpath(file_full_path)
                    # Build package path
                    package_path = ""
                    if targetIsDirectory:
                        # Have to watch out for 'relative' package loads not in a package when scanning directories
                        package_path = os.path.normpath(target_object)
                        if package_path == ".":
                            package_path = ""
                    else:
                        package_path = target_object.__name__
                    rel_path = root[len(search_path):]
                    print(rel_path)
                    if "\\" in rel_path:
                        # Fix Windows paths
                        rel_path = rel_path.replace("\\",".")
                    else:
                        # Fix *nix paths
                        rel_path = rel_path.replace("/", ".")
                    if targetIsDirectory and rel_path.startswith("."):
                        rel_path = rel_path[1:]
                    package_path += rel_path + f".{name[:-3]}"
                    if targetIsDirectory and package_path.startswith("."):
                        # Have to watch out for 'relative' package loads not in a package when scanning directories
                        package_path = package_path[1:]
                    file_mod_time = int(pathlib.Path(os.path.join(root, name)).stat().st_mtime)
                    addFileToDB(db_cursor, file_full_path, package_path, file_mod_time)
    db_conn.commit()
    return

def addFileToDB(db_cursor, file_full_path, package_path, file_mod_time):
    file_search = """
        SELECT
            fileID
        FROM
            Files
        WHERE package_path = ?
    """
    file_insert = """
        INSERT INTO Files (file_full_path, package_path, file_mod_time)
        VALUES (?, ?, ?)
    """
    # Does this package path already exist
    rows = db_cursor.execute(file_search, (package_path,)).fetchall()
    if len(rows) > 0:
        return
    
    # No, so add it
    db_cursor.execute(file_insert, (file_full_path, package_path, file_mod_time,))
    return

def getFileList(db_conn):
    """
    returns list of dictionaries like:
    {
        fileID:..,
        file_full_path:..,
        package_path:...,
        file_mod_time:...
    }
    """
    toreturn = []
    cursor = db_conn.cursor()
    stmt = """
        SELECT
            *
        FROM
            Files;
    """
    rows = cursor.execute(stmt)
    for row in rows:
        this_row = dict(zip(row.keys(), row))
        toreturn.append(this_row)
    return toreturn


                    
import inspect
import sys
from importlib import import_module

from .buildFileDB import getFileList
#from .cflow_importlib import import_module
from .callFlowData import callFlowData

def buildDeclaredEntitiesDB(db_conn):
    entities = findDeclaredEntities(db_conn)
   
    for entity in entities:
        addEntityToDB(db_conn.cursor(), **entity)
    db_conn.commit()

def addEntityToDB(db_cursor, fileID, entity_name, entity_type, import_path, py_obj, member_of_class = None):
    entity_search_stmt = """
        SELECT
            entityID
        FROM
            Entities
        WHERE
            entity_name = ? AND
            import_path = ?;
    """
    entity_insert_stmt = """
        INSERT INTO Entities (fileID, entity_name, entity_type, import_path, member_of_class)
        VALUES (?, ?, ?, ?, ?);
    """
    # Already exist?
    rows = db_cursor.execute(entity_search_stmt, (entity_name, import_path, )).fetchall()
    if len(rows) > 0:
        return

    # No, add it
    db_cursor.execute(entity_insert_stmt,
                      (fileID, entity_name, entity_type, import_path, member_of_class, ))
    # Get the new EntityID
    EntityID = -1
    for row in db_cursor.execute("select last_insert_rowid();"):
        EntityID = row[0]
        setattr(py_obj, "callflow_entity_id", row[0])
        setattr(py_obj, "callflow_file_id", fileID)

    return EntityID



def findDeclaredEntities(db_conn):
    """
    Will return list of entities like:
    {
        fileID:...,
        entity_name:...,
        entity_type:...,
        import_path:...,
    }
    """
    toreturn = []
    file_list = getFileList(db_conn)
    for f in file_list:
        try:
            entity = import_module(f["package_path"])
            fileID = f["fileID"]
            thisEntityItems = inspectEntity(entity, f["package_path"])
            for anEntity in thisEntityItems:
                anEntity["fileID"] = fileID
                toreturn += [anEntity]
        except Exception as badnews:
            print(f"Unable to process file {f['file_full_path']} because {badnews}", file=sys.stderr)
    return toreturn

def inspectEntity(entity, import_path="", member_of_class=None):
    # get all sub-entities
    sub_entities = []
    members = inspect.getmembers(entity)
    tgt_filename = inspect.getfile(entity)
    for m in members:
        try:
            element = getattr(entity, m[0])
            if inspect.getfile(element) == tgt_filename:
                # Only processing items defined in this file
                # Ignore code elements
                if not inspect.iscode(element):
                    sub_entities.append(element)
                    callFlowData().addDiscoveredObject(element)                    
        except TypeError:
            # Skipping things that aren't inspectable objects
            pass
        except Exception as badnews:
            print(
                f"pycallflow.buildDeclaredEntitiesDB.inspectEntity: unknown exception on entity {m[0]} -> {badnews}", file=sys.stderr)

    toreturn = []
    if inspect.ismodule(entity):
        # We need to find the entities in this module's file
        for se in sub_entities:
            toreturn += inspectEntity(se, import_path)
    elif inspect.isclass(entity):
        toreturn = [{
            "entity_name":entity.__name__,
            "entity_type":"class",
            "import_path":f"{import_path}",
            "py_obj":entity
        }]
        for se in sub_entities:
            toreturn += inspectEntity(se, f"{import_path}.{entity.__name__}")
    elif inspect.ismethod(entity):
        # This does not work because the entities are not properly "bound", so they all just register as functions
        if len(sub_entities) > 0:
            print(
                f"pycallflow.buildDeclaredEntitiesDB.inspectEntity: {entity.__name__} is a method but has sub_entities {sub_entities}", file=sys.stderr)
        toreturn = [{
            "entity_name":entity.__name__,
            "entity_type":"method",
            "import_path": f"{import_path}",
            "py_obj": entity,
            "member_of_class":member_of_class
        }]
    elif inspect.isfunction(entity):
        if len(sub_entities) > 0:
            print(
                f"pycallflow.buildDeclaredEntitiesDB.inspectEntity: {entity.__name__} is a function but has sub_entities {sub_entities}", file=sys.stderr)
        toreturn = [{
            "entity_name":entity.__name__,
            "entity_type":"function",
            "import_path": f"{import_path}",
            "py_obj": entity,
            "member_of_class":member_of_class,
        }]
    else:
        print(
            f"pycallflow.buildDeclaredEntitiesDB.inspectEntity: I don't know what {import_path}.{entity.__name__} is", file=sys.stderr)
        toreturn = []
    
    return toreturn

def findDeclaredEntities_inlineSave(db_conn):
    """
    Iterates files and finds entities, saving them inline
    """
    file_list = getFileList(db_conn)
    cursor = db_conn.cursor()
    for f in file_list:
        try:
            entity = import_module(f["package_path"])
            fileID = f["fileID"]
            inspectAndSaveEntities(cursor, fileID, entity, f["package_path"])
        except Exception as badnews:
            print(
                f"Unable to process file {f['file_full_path']} because {badnews}", file=sys.stderr)
    db_conn.commit()
    return 


def inspectAndSaveEntities(db_cursor, fileID, entity, import_path="", member_of_class=None):
    """
    This version does the same as above, but it saves and assigns EntityID as it goes to allow
    for assigning member_of_class correctly

    It does not return anything (data is saved as it goes)
    """
    # get all sub-entities
    sub_entities = []
    members = inspect.getmembers(entity)
    tgt_filename = inspect.getfile(entity)
    for m in members:
        try:
            element = getattr(entity, m[0])
            if inspect.getfile(element) == tgt_filename:
                # Only processing items defined in this file
                # Ignore code elements
                if not inspect.iscode(element):
                    sub_entities.append(element)
                    callFlowData().addDiscoveredObject(element)
        except TypeError:
            # Skipping things that aren't inspectable objects
            pass
        except Exception as badnews:
            print(
                f"callflow.buildDeclaredEntitiesDB.inspectEntity: unknown exception on entity {m[0]} -> {badnews}", file=sys.stderr)

    if inspect.ismodule(entity):
        # We need to find the entities in this module's file
        for se in sub_entities:
            inspectAndSaveEntities(db_cursor, fileID, se, import_path)
    elif inspect.isclass(entity):
        class_entityID = addEntityToDB(db_cursor, fileID, entity.__name__,
                      entity_type="class", import_path=f"{import_path}", py_obj=entity, member_of_class=member_of_class)
        for se in sub_entities:
            inspectAndSaveEntities(db_cursor, fileID,
                                               se, f"{import_path}.{entity.__name__}", class_entityID)
    elif inspect.ismethod(entity):
        # This does not work because the entities are not properly "bound", so they all just register as functions
        if len(sub_entities) > 0:
            print(
                f"callflow.buildDeclaredEntitiesDB.inspectEntity: {entity.__name__} is a method but has sub_entities {sub_entities}", file=sys.stderr)
        addEntityToDB(db_cursor, fileID, entity.__name__, entity_type="function",
                      import_path=f"{import_path}", py_obj=entity, member_of_class=member_of_class)
    elif inspect.isfunction(entity):
        if len(sub_entities) > 0:
            print(
                f"callflow.buildDeclaredEntitiesDB.inspectEntity: {entity.__name__} is a function but has sub_entities {sub_entities}", file=sys.stderr)
        addEntityToDB(db_cursor, fileID, entity.__name__, entity_type="function", import_path=f"{import_path}", py_obj=entity, member_of_class=member_of_class)
    else:
        print(
            f"callflow.buildDeclaredEntitiesDB.inspectEntity: I don't know what {import_path}.{entity.__name__} is", file=sys.stderr)

    return 


import dis

from .callFlowData import callFlowData

def buildCallflowDB(db_conn, suppress_calls_to_init):
    foundCalls = []
    objs_to_analyze = callFlowData().getDiscoveredObjects()
    entity_names, entity_data = entitylists(db_conn.cursor())
    for obj in objs_to_analyze:
        call_num = 0
        try:
            for t in dis.get_instructions(obj):
                if t.argval in entity_names:
                    if suppress_calls_to_init:
                        if t.argval == "__init__":
                            # We don't add it to the database.
                            continue
                    # Get all IDs with this name
                    for id in findAllEntityIDWithName(db_conn.cursor(), t.argval):
                        this_call = {
                            "fileID": obj.callflow_file_id,
                            "entityID": obj.callflow_entity_id, 
                            "called_entity_ID":id,
                            "collision_num": f"{obj.callflow_entity_id}.{call_num}"
                        }
                        foundCalls.append(this_call)
                        addCallDBEntry(db_conn.cursor(), **this_call)
                    call_num += 1
                elif t.opname == "LOAD_GLOBAL":
                    pass
        except Exception as badnews:
            pass
    db_conn.commit()

def entitylists(db_cursor):
    """
    returns names, data
    names = [ename1, ename2, ...]
        For fast lookup during disassembly
    data = [{info from the db}, {}]  These are in the same order as the object list due to algorithm
    """
    stmt = """
        SELECT
            *
        FROM
            Entities;
    """
    data = []
    names = []
    for row in db_cursor.execute(stmt):
        names.append(row["entity_name"])
        data.append(dict(zip(row.keys(), row)))
    return names, data

def findAllEntityIDWithName(db_cursor, entity_name):
    stmt = """
        SELECT
            entityID
        FROM
            Entities
        WHERE
            entity_name = ?;
    """
    toreturn = []
    for row in db_cursor.execute(stmt, (entity_name, )):
        toreturn.append(row["entityID"])
    return toreturn


def addCallDBEntry(db_cursor, entityID, called_entity_ID, collision_num, **kwargs):
    insert = """
        INSERT INTO Calls (entityID, called_entity_ID, collision_num)
        VALUES (?, ?, ?);
    """
    db_cursor.execute(insert, (entityID, called_entity_ID, collision_num, ))


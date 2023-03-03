import dis

from .callFlowData import callFlowData

def buildCallflowDB(db_conn, suppress_calls_to_init, match_to_file):
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
                    for id in findAllEntityIDWithName(db_conn.cursor(), t.argval, obj.callflow_file_id, match_to_file):
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

def findAllEntityIDWithName(db_cursor, entity_name, fileID, match_to_file=False):
    stmt = """
        SELECT
            entityID,
            fileID
        FROM
            Entities
        WHERE
            entity_name = ?;
    """
    toreturn = []
    possibles = []
    for row in db_cursor.execute(stmt, (entity_name, )):
        possibles.append(row["entityID"])
        if match_to_file and (row["fileID"] == fileID):
            toreturn.append(row["entityID"])

    # if there is nothing in toreturn, we set toreturn = possibles
    if len(toreturn) == 0:
        toreturn = possibles

    return toreturn


def addCallDBEntry(db_cursor, entityID, called_entity_ID, collision_num, **kwargs):
    insert = """
        INSERT INTO Calls (entityID, called_entity_ID, collision_num)
        VALUES (?, ?, ?);
    """
    db_cursor.execute(insert, (entityID, called_entity_ID, collision_num, ))


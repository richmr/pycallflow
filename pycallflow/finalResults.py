import networkx as nx
import sys

def generateFinalResults_object(db_conn):
    toreturn = {}
    for row in getFileEntityJoin(db_conn.cursor()):
        entity_name = row["entity_name"]
        if row["entity_type"] == "class":
            entity_name += ":"
        elif row["entity_type"] == "function":
            entity_name += "()"
        package_path = row["package_path"]
        if  package_path not in toreturn.keys():
            toreturn[package_path] = {
                "file_full_path":row["file_full_path"],
                "entities":[]
            }
        entity_to_add = {
            "entity_name":entity_name,
            "calls":[]
        }
        for row in getCallForEntity(db_conn.cursor(), row["entityID"]):
            these_calls = []
            called_entity_IDs = row["found_calls"].split(",")
            for id in called_entity_IDs:
                thiscall = getCallEntryForEntityID(db_conn.cursor(), int(id))
                these_calls.append(thiscall)
            entity_to_add["calls"].append(these_calls)
            
        toreturn[package_path]["entities"].append(entity_to_add)
    
    return toreturn


def getFileEntityJoin(db_cursor):
    # Returns list from SQL query
    stmt = """
        select
            Files.fileID,
            file_full_path,
            package_path,
            entityID,
            entity_name,
            entity_type,
            import_path
        from
            Entities
        JOIN
            Files on Entities.fileID=Files.fileID;
    """
    return db_cursor.execute(stmt).fetchall()

def getCallForEntity(db_cursor, entityID):
    # returns list from SQL query
    # Ambiguous calls represented by concatenated list of called entity ID
    stmt = """
        select
            entityID,
            GROUP_CONCAT(called_entity_ID) as found_calls
        from
            Calls
        group by
            collision_num
        having
            entityID = ?;
    """
    return db_cursor.execute(stmt, (entityID, )).fetchall()

def getInfoForEntity(db_cursor, entityID):
    # returns a dict
    stmt = """
        SELECT
            entity_name,
            entity_type,
            import_path
        FROM
            Entities
        WHERE
        entityID = ?;
    """
    toreturn = {}
    for row in db_cursor.execute(stmt, (entityID,)):
        toreturn = dict(zip(row.keys(), row))
        break
    return toreturn

def getCallEntryForEntityID(db_cursor, entityID):
    """
    Produces a:
    {
        import_path:..,
        entity_name: ...[()|:] 
    }
    For adding to final results
    """
    toreturn = getInfoForEntity(db_cursor, entityID)
    # Adding some decorators to allow easy ID in final report
    if toreturn["entity_type"] == "class":
        toreturn["entity_name"] += ":"
    elif toreturn["entity_type"] == "function":
        toreturn["entity_name"] += "()"
    return toreturn

"""
Might need:
{
    EntityID: {
        "file_import_path":importpath,
        "name": ... (add () or :)
        "member_of_class":None or Entity ID
        "calls":[
                    # No collision
                    [
                        entity_id
                    ],
                    # collision (len of list > 1)
                    [
                        entity_id, entity_id2
                    ]
                ]

    }
}
"""


def generateEntityResults_selectID_object(
        db_conn,
        select_entity_id,
):
    results_object = generateEntityResults_object(db_conn)
    # return results_object

    if select_entity_id is None:
        return results_object

    # if there are select_entity_id, we make a quick networkx graph and use it to trace the call flows
    nx_g = nx.DiGraph()
    
    for n, (k, v) in enumerate(results_object.items()):
        for call in v["calls"]:
            for to_id in call:
                if k == to_id:
                    continue
                nx_g.add_edge(k, to_id)

    try:
        select_entity_id_list = [int(i) for i in select_entity_id.split(",")]
    except Exception as badnews:
        print(
            f"generateFinalResults_selectID_object: Unable to parse select_entity_id: {select_entity_id}", sys.stderr)
        return results_object

    # now trace the results
    # only do this once
    nx_g_reverse = nx_g.reverse()
    list_of_nodes_to_keep = select_entity_id_list.copy()
    for node_id in select_entity_id_list:
        # Forward first
        successor_nodes_dict = nx.dfs_successors(nx_g, source=node_id)
        for n, (n_id, called_nodes_list) in enumerate(successor_nodes_dict.items()):
            list_of_nodes_to_keep += called_nodes_list

        predecessor_nodes_dict = nx.dfs_successors(nx_g_reverse, source=node_id)
        for n, (n_id, called_nodes_list) in enumerate(predecessor_nodes_dict.items()):
            list_of_nodes_to_keep += called_nodes_list

    # remove duplicates
    list_of_nodes_to_keep = list(set(list_of_nodes_to_keep))

    # We need to add in the classes for these entities
    for entityID in list_of_nodes_to_keep:
        if results_object[entityID]["member_of_class"] is not None:
            list_of_nodes_to_keep.append(results_object[entityID]["member_of_class"])

    # create new "final results" for just these entities
    pruned_results_obj = {id: results_object[id] for id in list_of_nodes_to_keep}
    return pruned_results_obj

def generateEntityResults_object(db_conn):
    toreturn = {}
    for row in getEntityJoin(db_conn.cursor()):
        this_entity_data = dict(zip(row.keys(), row))
        if this_entity_data["entity_type"] == "class":
            this_entity_data["name"] += ":"
        elif this_entity_data["entity_type"] == "function":
            this_entity_data["name"] += "()"
        this_entity_data["calls"] = []
        for call_row in getCallForEntity(db_conn.cursor(), row["entityID"]):
            these_calls = [int(called_id) for called_id in call_row["found_calls"].split(",")]
            this_entity_data["calls"].append(these_calls)
        toreturn[this_entity_data["entityID"]] = this_entity_data
    return toreturn

def getEntityJoin(db_cur):
    stmt = """
        select
            entityID,
            entity_name as name,
            Files.package_path as file_import_path,
            member_of_class,
            entity_type
        from
            Entities
        JOIN
            Files on Entities.fileID=Files.fileID;
    """
    return db_cur.execute(stmt).fetchall() 

def getEntityList(db_conn):
    toreturn = [dict(zip(row.keys(), row)) for row in getEntityJoin(db_conn.cursor())]
    return toreturn

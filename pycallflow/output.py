
import networkx as nx
import pydot
from collections import deque
from tabulate import tabulate
import sys

from pprint import pprint

def simpleTextOutput(finalOutputDataObject):
    for n, (k, v) in enumerate(finalOutputDataObject.items()):
        print(f"Module: {k}")
        print(f"({v['file_full_path']})")
        print("Defines:")
        for e in v['entities']:
            print(f"\t- {e['entity_name']}")
            if len(e['calls']) == 0:
                print("\t\t-- No external calls")
            else:
                for call_list in e['calls']:
                    if len(call_list) == 1:
                        print(f"\t\t-- Calls {call_list[0]['entity_name']} from {call_list[0]['import_path']}")
                    else:
                        print(f"\t\t-- Ambiguous call, may call any of these:")
                        for acall in call_list:
                            print(f"\t\t\t-- Calls {acall['entity_name']} from {acall['import_path']}")
        print()

def networkx_dot_output(finalOutputDataObject):
    """
    Generates and emits DOT compatible graph output
    """
    call_pairs = []
    for n, (k, v) in enumerate(finalOutputDataObject.items()):
        module_path = k
        for e in v['entities']:
            from_e = f"{module_path}.{e['entity_name']}"
            for call_list in e['calls']:
                for acall in call_list:
                    to_e = f"{acall['import_path']}.{acall['entity_name']}"
                    call_pairs.append((from_e, to_e))
    
    nx_out = nx.DiGraph(call_pairs)
    dot_out = nx.nx_pydot.to_pydot(nx_out)
    print(dot_out.to_string())

def entity_list_output(entityListObject):
    dataList = [[entity['entityID'], entity['name'], entity['entity_type'], entity['file_import_path']] for entity in entityListObject]
    headers = ['entityID', 'name', 'Type', 'import path']
    print(tabulate(dataList, headers=headers, tablefmt="github"))

class pydot_output:

    def __init__(self):
        self.init_x11_colors()
        pass

    def output(self, finalOutputDataObject, /,
        rankdir,
        edge_color,
        suppress_recursive_calls,
        combine_calls,
        suppress_class_references,
        graph_name = "Callflow Analysis",
        **kwargs
    ):
        graph = pydot.Graph(graph_name, compound=True, rankdir=rankdir)
        file_clusters = {}
        class_clusters = {}
        # First generate the file clusters, class clusters, and add a node to each entity
        for n, (k, v) in enumerate(finalOutputDataObject.items()):
            if v["file_import_path"] not in file_clusters.keys():
                file_clusters[v["file_import_path"]] = pydot.Cluster(v["file_import_path"], label=v["file_import_path"])
                # add it to the graph
                graph.add_subgraph(file_clusters[v["file_import_path"]])
            fc = file_clusters[v["file_import_path"]]
            cc = None
            if v["member_of_class"] is not None:
                if v["member_of_class"] not in class_clusters.keys():
                    # Make a new Cluster for this graph
                    class_clusters[v["member_of_class"]] = pydot.Cluster(
                        finalOutputDataObject[v["member_of_class"]]["name"], label=finalOutputDataObject[v["member_of_class"]]["name"])
                    #  Add it to the proper file cluster
                    fc.add_subgraph(class_clusters[v["member_of_class"]])
                cc = class_clusters[v["member_of_class"]]

            # Make the initial node
            this_node = pydot.Node(name=str(k), label=v["name"])
            if v["entity_type"] == "class":
                # Make sure it has a Cluster
                if k not in class_clusters.keys():
                    # Make a new Cluster for this graph
                    class_clusters[k] = pydot.Cluster(str(k), label=v["name"])
                    #  Add it to the proper file cluster
                    fc.add_subgraph(class_clusters[k])

                if suppress_class_references:
                    # Then we don't need to continue with this node
                    continue

                # Classes need to have an extra node added to show references to the class, even though methods might not be called
                this_node.set_label(v["name"]+" (ref)")
                # Add it to its own class cluster
                cc = class_clusters[k]
            
            if cc is not None:
                cc.add_node(this_node)
            else:
                fc.add_node(this_node)

            v["node"] = this_node

        # Now make the edges
        edge_list = []
        for n, (k, v) in enumerate(finalOutputDataObject.items()):
            if "node" not in v.keys():
                # Then this is probably a skipped class reference and there should be no calls
                continue
            from_node = v["node"]
            for call in v["calls"]:
                style = "solid"
                color = edge_color
                if edge_color == "rotate":
                    color = self.next_X11_color()
                if len(call) > 1:
                    style = "dashed"    # Represents an ambiguous call to entities of same name
                for to_id in call:
                    if to_id not in finalOutputDataObject.keys():
                        # Then it was pruned.
                        continue
                    edge_id = f"{k},{to_id}"
                    if suppress_recursive_calls:
                        if k == to_id:
                            continue
                    if combine_calls:
                        if edge_id in edge_list:
                            # Already have this one
                            continue
                    if suppress_class_references:
                        if finalOutputDataObject[to_id]["entity_type"] == "class":
                            # don't draw it
                            continue
                    to_node = finalOutputDataObject[to_id]["node"]
                    graph.add_edge(pydot.Edge(from_node, to_node, style=style, color=color))
                    edge_list.append(edge_id)

        print(graph.to_string())

    def init_x11_colors(self):
        self.x11_colors_d = deque([
            'aquamarine',
            'antiquewhite4',
            'aquamarine3',
            'azure3',
            'bisque2',
            'blue',
            'blueviolet',
            'brown4',
            'burlywood4',
            'cadetblue4',
            'chartreuse4',
            'chocolate4',
            'coral3',
            'cornsilk3',
            'cyan2',
            'darkgoldenrod',
            'darkgray',
            'darkolivegreen',
            'darkorange',
            'darkorchid',
            'darkred',
            'darkseagreen3',
            'darkslategray2',
            'darkviolet',
            'deeppink4',
            'deepskyblue4',
            'dodgerblue2',
            'firebrick2',
            'gold2',
            'goldenrod2',
        ])

    def next_X11_color(self):
        color = self.x11_colors_d[0]
        self.x11_colors_d.rotate(1)
        return color








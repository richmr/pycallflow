from contextlib import closing, redirect_stdout
import argparse
import importlib
from pprint import pprint
import sys
import os
import traceback

from .callFlowData import callFlowData
from .buildFileDB import buildFileDB
from .buildDeclaredEntitiesDB import findDeclaredEntities_inlineSave
from .analyzeCallFlow import buildCallflowDB
from .finalResults import generateFinalResults_object, generateEntityResults_selectID_object, getEntityList
from .output import simpleTextOutput, pydot_output, entity_list_output, all_entity_flow

    
def cli_run():
    version = "0.1.0"
    #  Arguments
    description = f"pycallflow v{version}: "
    description += "Maps call flows in python packages, modules, and directories"
    parser = argparse.ArgumentParser(
        description=description, prog="pycallflow")
    parser.add_argument(
        "target", help="Package or module name to attempt to map")
    parser.add_argument("-d", "--directory", action="store_true",
                        help="Consider the 'target' argument a directory, not a package")
    parser.add_argument("-o", "--output", choices=["dot", "simple", "entity_list", "entity_flow_graphs"], type=str, default="dot",
                        help="Choose output type.  'dot' will produce dot-compatible drawing output. 'entity_list' provides table of discovered entity names for use in --select_entity_id. 'entity_flow_graphs' will make pycallflow generate a --clean callflow for every function and method entity found (__init__ and __del__ are ignored).  Files will be named by their 'import path' and 'name' and are stored as defined by --save_images_to.  This assumes graphviz is working on your system.  Images are pngs.")
    parser.add_argument("--rankdir", type=str, choices=[
                        "TB", "BT", "RL", "LR"], default="LR", help="See Graphviz documentation")
    parser.add_argument("--edge_color", type=str, default="rotate",
                        help="Use an X11 color scheme name or 'rotate' to rotate through X11 colors")
    parser.add_argument("--suppress_recursive_calls", action="store_true", help="Hides edges for entities that call themselves")
    parser.add_argument("--combine_calls", action="store_true", help="Will only show one directed edge between two entities, regardless of actual number of calls")
    parser.add_argument("--suppress_class_references", action="store_true", help="Will suppress explicit edges representing references to a class (method calls will remain)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Provide some feedback on progress")
    parser.add_argument("--db_file", type=str, default=":memory:", help="pycallflow uses an in memory sqlite3 database normally, specify another filename here if you want it stored to disk for your future analysis.")
    parser.add_argument("--stdout_capture_file", type=str, default=os.devnull, help="Since the examined code is actually imported any code not protected with a __main__ clause will run. Stdout is normally redirected to os.devnull to prevent output corruption.  Specify another filename if you would like to capture the output from the analyzed code.")
    parser.add_argument("--select_entity_id", type=str, default=None,
                        help="Comma separated list of specific entity ID numbers to trace.  Use -oentity_list to get the entity ID.  The entity ID will remain constant if there are no changes to the files or added files.")
    parser.add_argument("--suppress_calls_to_init", action="store_true", help="Will not show calls going to __init__ functions.  These can be very noisy if a superclass has many subclasses.")
    parser.add_argument("--clean", action="store_true", help="Will set all graph simplification options to true")
    parser.add_argument("--match_to_file", action="store_true", help="Ambiguous calls happen if there are multiple entities with the same name in seprate files.  Setting this flag will make pycallflow choose calls from the same file, if they exist")
    #parser.add_argument("--generate_entity_flows", action="store_true", help="Set this flag to make pycallflow generate a --clean callflow for every function and method entity found (__init__ and __del__ are ignored).  Files will be named by their 'import path' and 'name' and are stored as defined by --save_images_to.  This assumes graphviz is working on your system.  Images are pngs.")
    parser.add_argument("--save_images_to", type=str, default="images", help="Set this to the directory you want -o entity_flow_graphs to save the images")
    ### Not implemented
    # parser.add_argument("--highlight_orphans", action="store_true", help="Will highlight entities that are never called (possible dead code).  Only does anything in with 'dot' output")
    
    args = parser.parse_args()

    # Make copy of args for future mod:
    args_cp = vars(args).copy()

    if args_cp["clean"]:
        # Set all simplicification to true
        args_cp["suppress_recursive_calls"] = True
        args_cp["combine_calls"] = True
        args_cp["suppress_class_references"] = True
        args_cp["suppress_calls_to_init"] = True
        args_cp["match_to_file"] = True
    
    cf_data = collectData(**args_cp)
    with cf_data.getSqliteConnection() as conn:
        if args.output == "entity_list":
            results = getEntityList(conn)
            entity_list_output(results)
        elif args.output == "dot":
            results = generateEntityResults_selectID_object(conn, select_entity_id=args.select_entity_id)
            pydot_output().output(results, **args_cp)
        elif args.output == "entity_flow_graphs":
            try:
                aef = all_entity_flow(args.save_images_to)
                aef.generate_all_entity_flows(conn, **args_cp)
            except FileNotFoundError:
                
                print("'entity_flow_graphs' mode requires Graphviz and dot to be installed and on the system path")
                return
            except NotADirectoryError:
                print(f"The {args.save_images_to} directory does not exist, please create it and try again")
                return
            except Exception as badnews:
                # traceback.print_exc()
                print(f"Unable to complete processing because {badnews}")
                return
        else:
            results = generateFinalResults_object(conn)
            simpleTextOutput(results)

def collectData( # See argparse list in cli_run()
    target,
    directory = False,
    db_file = ":memory:",
    verbose = False,
    stdout_capture_file = os.devnull,
    suppress_calls_to_init = False,
    match_to_file = False,
    **kwargs        # Catch all     
):
    """
    target - name of package or directory to analyze
    directory - set True if the target is a directory and not a package [False]
    db_file - Name of sqlite3 db file to generate [:memory:]
    verbose - Set True for status updates [False]
    stdout_capture_file  - filename to capture any output from the analyzed code [os.devnull]
    """
    verbose_out_f = None
    cf_data = None
    if verbose:
        verbose_out_f = sys.stderr
    else:
        verbose_out_f = open(os.devnull, "w")
    # Begin redirecting stdout    
    with open(stdout_capture_file, "w") as stdout_cap:
        with redirect_stdout(stdout_cap):
            # import the target
            target_obj = ""
            if directory:
                target_obj = target
            else:
                target_obj = importlib.import_module(target)

            cf_data = callFlowData(sqlite3_filename=db_file)
            with cf_data.getSqliteConnection() as conn:
                db_cursor = conn.cursor()
                print("[-] Clearing old data", file=verbose_out_f)
                cf_data.clearTables(conn)
                print("[-] Building file list", file=verbose_out_f)
                buildFileDB(target_obj, conn, directory)
                print("[-] Building declared entity DB", file=verbose_out_f)
                findDeclaredEntities_inlineSave(conn)
                print(
                    f"[-] Found {len(cf_data.getDiscoveredObjects())} objects", file=verbose_out_f)
                buildCallflowDB(conn, suppress_calls_to_init, match_to_file)
    
    if not verbose:
        # Make sure to clean up the os.devnull file
        verbose_out_f.close()

    return cf_data        
    

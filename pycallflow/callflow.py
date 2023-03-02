from contextlib import closing, redirect_stdout
import argparse
import importlib
from pprint import pprint
import sys
import os

from .callFlowData import callFlowData
from .buildFileDB import buildFileDB
from .buildDeclaredEntitiesDB import findDeclaredEntities_inlineSave
from .analyzeCallFlow import buildCallflowDB
from .finalResults import generateFinalResults_object, generateEntityResults_selectID_object, getEntityList
from .output import simpleTextOutput, pydot_output, entity_list_output

    
def cli_run():
    version = "Dev"
    #  Arguments
    description = f"pycallflow v{version}: "
    description += "Maps call flows in python packages, modules, and directories"
    parser = argparse.ArgumentParser(
        description=description, prog="pycallflow")
    parser.add_argument(
        "target", help="Package or module name to attempt to map")
    parser.add_argument("-d", "--directory", action="store_true",
                        help="Consider the 'target' argument a directory, not a package")
    parser.add_argument("-o", "--output", choices=["dot", "simple", "entity_list"], type=str, default="dot",
                        help="Choose output type.  'dot' will produce dot-compatible drawing output. 'entity_list' provides table of discovered entity names for use in --select_entity_id.")
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
    ### Not implemented
    # parser.add_argument("--highlight_orphans", action="store_true", help="Will highlight entities that are never called (possible dead code).  Only does anything in with 'dot' output")
    
    args = parser.parse_args()
    
    cf_data = collectData(**vars(args))
    with cf_data.getSqliteConnection() as conn:
        if args.output == "entity_list":
            results = getEntityList(conn)
            entity_list_output(results)
        elif args.output == "dot":
            results = generateEntityResults_selectID_object(conn, select_entity_id=args.select_entity_id)
            pydot_output().output(results, **vars(args))
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
                buildCallflowDB(conn, suppress_calls_to_init)
    
    if not verbose:
        # Make sure to clean up the os.devnull file
        verbose_out_f.close()

    return cf_data        
    

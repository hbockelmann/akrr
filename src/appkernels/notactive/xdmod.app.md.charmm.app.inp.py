name = """xdmod.app.md.charmm"""
nickname = """xdmod.app.md.charmm.@ncpus@"""
uri = """file:///home/charngda/Inca-Reporter//xdmod.app.md.charmm"""
context = '''@batchpre@ -nodes=:@ppn@:@ncpus@ -type=@batchFeature@ -walllimit=@walllimit@ -exec="@@"'''
resourceSetName = """defaultGrid"""
action = """add"""
schedule = [
    """? ? */12 * *""",
]
arg_version = """no"""
arg_verbose = 1
arg_help = """no"""
arg_bin_path = """@bin_path@"""
arg_log = 5
walllimit=10


parser="xdmod.app.md.charmm.py"
#path to run script relative to AppKerDir on particular resource
runScriptPath="charmm/run"
runScriptArgs="input01"

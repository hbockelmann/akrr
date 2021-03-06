name = """xdmod.app.phys.quantum_espresso"""
nickname = """xdmod.app.phys.quantum_espresso.@ncpus@"""
uri = """file:///home/charngda/Inca-Reporter//xdmod.app.phys.quantum_espresso"""
context = '''@batchpre@ -nodes=:@ppn@:@ncpus@ -type=@batchFeature@ -walllimit=@walllimit@ -exec="@@"'''
resourceSetName = """defaultGrid"""
action = """add"""
schedule = [
    """? ? */14 * *""",
]
arg_version = """no"""
arg_verbose = 1
arg_help = """no"""
arg_bin_path = """@bin_path@"""
arg_log = 5
walllimit=15

parser="xdmod.app.phys.quantum_espresso.py"
#path to run script relative to AppKerDir on particular resource
runScriptPath="quantum_espresso/run"
runScriptArgs="input01"
name = """xdmod.benchmark.graph.graph500"""
nickname = """xdmod.benchmark.graph.graph500.@ncpus@"""
uri = """file:///home/charngda/Inca-Reporter//xdmod.benchmark.graph.graph500"""
context = '''@batchpre@ -nodes=:@ppn@:@ncpus@ -type=@batchFeature@ -walllimit=@walllimit@ -exec="@@"'''
resourceSetName = """defaultGrid"""
action = """add"""
schedule = [
    """? ? 0-31/14 * *""",
]
arg_version = """no"""
arg_verbose = 1
arg_help = """no"""
arg_bin_path = """@bin_path@"""
arg_log = 5
walllimit=15
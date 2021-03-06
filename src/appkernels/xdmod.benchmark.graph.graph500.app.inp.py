info = ""

walllimit=30
parser="xdmod.benchmark.graph.graph500.py"
#path to run script relative to AppKerDir on particular resource
executable="execs/graph500/mpi214/graph500_mpi_replicated_csc_seqval"
input="inputs/graph500/input23"


runScriptPreRun="""
#create working dir
export AKRR_TMP_WORKDIR=`mktemp -d {networkScratch}/ior.XXXXXXXXX`
echo "Temporary working directory: $AKRR_TMP_WORKDIR"
cd $AKRR_TMP_WORKDIR

#set executable location
EXE={appKerDir}/{executable}

"""
runScriptPostRun="""#clean-up
cd $AKRR_TASK_WORKDIR
if [ "${{AKRR_DEBUG=no}}" = "no" ]
then
        echo "Deleting temporary files"
        rm -rf $AKRR_TMP_WORKDIR
else
        echo "Copying temporary files"
        cp -r $AKRR_TMP_WORKDIR workdir
        rm -rf $AKRR_TMP_WORKDIR
fi
"""



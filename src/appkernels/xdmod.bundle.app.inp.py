walllimit=60*3

parser="xdmod.bundle.py"

shuffleSubtasks=True

#path to run script relative to AppKerDir on particular resource
executable="execs"
input="inputs"

runScriptPreRun="""#create working dir
export AKRR_TMP_WORKDIR=`mktemp -d {networkScratch}/xdmod.bundle.XXXXXXXXX`
echo "Temporary working directory: $AKRR_TMP_WORKDIR"
cd $AKRR_TMP_WORKDIR

"""
appKernelRunEnvironmentTemplate=""

akrrGenerateAppKernelSignature=""

akrrRunAppKernelTemplate="""
#Load application environment
module list

{subTasksExecution}
"""

runScriptPostRun="""
#clean-up
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





#Remote access method to the resource (default ssh)
remoteAccessMethod = 'ssh'
#Remote copy method to the resource (default scp)
remoteCopyMethod='scp'

sshPassword = None
sshPrivateKeyFile = None
sshPrivateKeyPassword = None

#Scratch visible across all nodes
networkScratch='$SCRATCH'
#Local scratch only locally visible
localScratch='/tmp'

#master batch job script template
batchJobTemplate="""{batchJobHeaderTemplate}

{akrrCommonCommands}

{akrrRunAppKer}

{akrrCommonCleanup}
"""

#Template for common Parameters
akrrCommonCommandsTemplate='''#Common commands
export AKRR_NODES={akrrNNodes}
export AKRR_CORES={akrrNCores}
export AKRR_CORES_PER_NODE={akrrPPN}
export AKRR_NETWORK_SCRATCH="{networkScratch}"
export AKRR_LOCAL_SCRATCH="{localScratch}"
export AKRR_TASK_WORKDIR="{akrrTaskWorkingDir}"
export AKRR_APPKER_DIR="{appKerDir}"
export AKRR_AKRR_DIR="{akrrData}"

export AKRR_APPKER_NAME="{akrrAppKerName}"
export AKRR_RESOURCE_NAME="{akrrResourceName}"
export AKRR_TIMESTAMP="{akrrTimeStamp}"
export AKRR_APP_STDOUT_FILE="$AKRR_TASK_WORKDIR/appstdout"

export AKRR_APPKERNEL_INPUT="{appKerDir}/{input}"
export AKRR_APPKERNEL_EXECUTABLE="{appKerDir}/{executable}"

source "$AKRR_APPKER_DIR/execs/bin/akrr_util.bash"

#Populate list of nodes per MPI process
{nodeListSetterTemplate}

export PATH="$AKRR_APPKER_DIR/execs/bin:$PATH"

cd "$AKRR_TASK_WORKDIR"

#run common tests
akrrPerformCommonTests

#Write some info to gen.info, JSON-Like file
writeToGenInfo "startTime" "`date`"
writeToGenInfo "nodeList" "$AKRR_NODELIST"
'''

akrrRunAppKer="""{runScriptPreRun}

{appKernelRunEnvironmentTemplate}

{akrrGenerateAppKernelSignature}

{akrrRunAppKernelTemplate}

{runScriptPostRun}
"""

appKernelRunEnvironmentTemplate=""

akrrGenerateAppKernelSignature="""#Generate AppKer signature
appsigcheck.sh $EXE $AKRR_TASK_WORKDIR/.. > $AKRR_APP_STDOUT_FILE
"""

#default template for app kernel launching
akrrRunAppKernelTemplate="""#Execute AppKer
writeToGenInfo "appKerStartTime" "`date`"
$RUN_APPKERNEL >> $AKRR_APP_STDOUT_FILE 2>&1
writeToGenInfo "appKerEndTime" "`date`"
"""

akrrCommonCleanupTemplate='writeToGenInfo "endTime" "`date`"'

#network file system hints 
mpi_io_hints=""

#Node list setter
nodeListSetter={
    'pbs':"""export AKRR_NODELIST=`cat $PBS_NODEFILE`""",
    'slurm':"""export AKRR_NODELIST=`srun -l --ntasks-per-node=$AKRR_CORES_PER_NODE -n $AKRR_CORES hostname -s|sort -n| awk '{{printf "%s ",$2}}' `"""
}

#common commands among resources to be executed prior the application kernel execution
#usually copying of input parameters, application signature calculation
runScriptPreRun="""#create working dir
export AKRR_TMP_WORKDIR=`mktemp -d {networkScratch}/ak.XXXXXXXXX`
echo "Temporary working directory: $AKRR_TMP_WORKDIR"
cd $AKRR_TMP_WORKDIR

#Copy inputs
if [ -d "{appKerDir}/{input}" ]
then
    cp {appKerDir}/{input}/* ./
fi
if [ -f "{appKerDir}/{input}" ]
then
    cp {appKerDir}/{input} ./
fi
"""

#common commands among resources to be executed after the application kernel execution
#usually cleaning up
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

#shell to use
shell="bash"

info=""

autoWalltimeLimit=True

autoWalltimeLimitOverhead=0.2


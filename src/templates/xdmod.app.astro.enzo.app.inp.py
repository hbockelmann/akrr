appKernelRunEnvironmentTemplate="""
#Load application environment
module purge
module load mvapich2/intel-13.1/2-2.0a-QLogic
module load hdf
module list

#set executable location
#source {appKerDir}/{executable}/../../bin/activate.csh
EXE={appKerDir}/{executable}/src/enzo/enzo.exe
ring_bin={appKerDir}/{executable}/src/ring/ring.exe
inits_bin={appKerDir}/{executable}/src/inits/inits.exe
"""

akrrRunAppKernelTemplate="""#Execute AppKer
mpiexec -np 1 $EXE -V >> $AKRR_APP_STDOUT_FILE 2>&1
$inits_bin input.inits >> $AKRR_APP_STDOUT_FILE 2>&1
srun --mpi=pmi2  $ring_bin pv ParticlePositions ParticleVelocities >> $AKRR_APP_STDOUT_FILE 2>&1
srun --mpi=pmi2  $EXE input.enzo >> $AKRR_APP_STDOUT_FILE 2>&1
echo performance.out >> $AKRR_APP_STDOUT_FILE 2>&1
cat performance.out >> $AKRR_APP_STDOUT_FILE 2>&1

{runScriptPostRun}
"""



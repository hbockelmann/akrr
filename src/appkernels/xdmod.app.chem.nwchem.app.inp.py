walllimit=22

parser="xdmod.app.chem.nwchem.py"

#path to run script relative to AppKerDir on particular resource
executable="execs"
input="inputs/nwchem/aump2.nw"


runScriptPreRun="""#create working dir
export AKRR_TMP_WORKDIR=`mktemp -d {networkScratch}/nwchem.XXXXXXXXX`
echo "Temporary working directory: $AKRR_TMP_WORKDIR"
cd $AKRR_TMP_WORKDIR

#Copy inputs
cp {appKerDir}/{input} ./
INPUT=$(echo {appKerDir}/{input} | xargs basename )

# set the NWCHEM_PERMANENT_DIR and NWCHEM_SCRATCH_DIR in the input file
# first, comment out any NWCHEM_PERMANENT_DIR and NWCHEM_SCRATCH_DIR in the input file
if [ -e $INPUT ]
then
    sed -i -e "s/scratch_dir/#/g" $INPUT
    sed -i -e "s/permanent_dir/#/g" $INPUT
    # then add our own
    echo "scratch_dir $AKRR_TMP_WORKDIR" >> $INPUT
    echo "permanent_dir $AKRR_TMP_WORKDIR" >> $INPUT
fi
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

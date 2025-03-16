#!/bin/bash

## Execute GCsnap without annotation for various threads with mmseqs all-against-all
## Run on amd partition as this is connected to www

# define paths
source_p=/users/stud/k/kruret00/MT/GCsnap/   # GCsnap run folder
target_p=/users/stud/k/kruret00/PASC25/experiments_deliver/gcsnap1/  # experiment result folder
target_files=/users/stud/k/kruret00/PASC25/targets/  # files with targets


## run parallel version (1 2 4 8)
for threads in  1 2 4 8
do
	## targets (10 20 50 100)
	for targets in 10 20 50 100
	do
	
		# number of repetitions
		for repetition in {1..5};
		do
	
			ident=${targets}_${threads}_${repetition}
			
			sbatch 	--export=ALL,source_p=${source_p},target_p=${target_p},target_files=${target_files},targets=${targets},threads=${threads},ident=${ident},repetition=${repetition} \
					--job-name=${ident} \
					--nodes=1 \
					--ntasks-per-node=1 \
					--output=${target_p}run_${ident}.out \
					${target_p}run.job
					
			sleep 0.25
		done
	done
done


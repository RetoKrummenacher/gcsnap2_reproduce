#!/bin/bash

## script to run GCsnap cluster
path=/users/stud/k/kruret00/PASC25/
gcsnap_path=/users/stud/k/kruret00/gcsnap2cluster/
exp_path=${path}/experiments_deliver/setC/
target_files=${path}targets/

## load Python module
ml Python

# how many repetitions
repetitions=5

# Define the specific (ranks_per_node, cpus_per_rank) combinations
combinations=(
	"4 8"
	"4 16"
	"4 32"
    "8 8"
	"8 16"
)

## targets loop
for n_targets in 10000
do
	## nodes (1)
	for nodes in 1
	do

		for combo in "${combinations[@]}"
		do
			# Extract values
			read ranks_per_node cpus_per_rank <<< "$combo"

			if (( ${ranks_per_node} * ${cpus_per_rank} > 128 ))
			then
				continue
			else

				## repetition loop
				for (( rep=1; rep<=${repetitions}; rep++ ))
				do

					ident=${n_targets}_${nodes}_${ranks_per_node}_${cpus_per_rank}_${rep}

					sbatch 	--export=ALL,exp_path=${exp_path},gcsnap_path=${gcsnap_path},target_files=${target_files},n_targets=${n_targets},nodes=${nodes},ranks_per_node=${ranks_per_node},cpus_per_task=${cpus_per_rank},rep=${rep},ident=${ident} \
							--job-name=${ident} \
							--nodes=${nodes}  \
							--ntasks-per-node=${ranks_per_node} \
							--cpus-per-task=${cpus_per_rank} \
							--output=${exp_path}run_${ident}.out \
							${exp_path}run.job

					sleep 0.2						
				done
			fi
		done
	done
done

#!/bin/bash

## script to run GCsnap cluster
path=/.../
gcsnap_path=/.../gcsnap2cluster/  # cloned GCsnap2 Cluster repository
exp_path=${path}/experiments/gcsnap2/
target_files=${path}targets/

## load Python module
ml Python

# how many repetitions
repetitions=5

## targets loop
for n_targets in 1000
do
	## nodes (4,8,16)
	for nodes in 8
	do
		## ranks on each node (2,4,8,16)
		for ranks_per_node in 4
		do
			## cpus per rank (1,2,4)
			for cpus_per_rank in 4
			do

				if (( ${ranks_per_node} * ${cpus_per_rank} > 20 ))
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
done

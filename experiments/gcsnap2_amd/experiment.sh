#!/bin/bash

## script to run GCsnap cluster
path=/.../
gcsnap_path=/.../gcsnap2cluster/ # cloned GCsnap2 Cluster repository
exp_path=${path}/experiments/gcsnap2_amd/
target_files=${path}targets/

## load Python module
ml Python

# how many repetitions
repetitions=1

## targets loop
for n_targets in 10000
do
	## nodes (1)
	for nodes in 1
	do
		# tested combintations (8,16),(12,10),(16,8),(32,4)
		## ranks on each node 
		for ranks_per_node in 8
		do
			## cpus per rank 
			for cpus_per_rank in 16
			do

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
done

#!/bin/bash

## script to run assembly parsing with mpi4py.futures.


path=/.../experiments/
exp_path=${path}mpi_distributed_assemblies/
result_path=${exp_path}results/

# clear all results
rm ${result_path}*.csv
rm ${result_path}*.out

## how many repetitions
repetitions=5

## targets loop
for n_targets in 1000 5000 10000
do		
	for nodes in 1 2 4 8 16
	do
		## ranks on each node
		for ranks_per_node in 1 2 4 8 16
		do		
					
			## repetition loop
			for (( rep=1; rep<=${repetitions}; rep++ ))
			do		
				ident=${n_targets}_${nodes}_${ranks_per_node}_${rep}
			
				## exported are all the arguments needed for the Python script
				## slurm configuration (e.g., --nodes) are set here when changing during iterations
				sbatch 	--export=ALL,exp_path=${exp_path},result_path=${result_path},n_targets=${n_targets},nodes=${nodes},ranks_per_node=${ranks_per_node},repetition=${rep} \
						--job-name=${ident} \
						--nodes=${nodes}  \
						--ntasks-per-node=${ranks_per_node} \
						--cpus-per-task=1 \
						--output=${result_path}${ident}.out \
						${exp_path}mpi_distributed_assemblies.job
									
				sleep 0.2	
			done
		done 
	done
done 
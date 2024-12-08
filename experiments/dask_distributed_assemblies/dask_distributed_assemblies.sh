#!/bin/bash

## script to run assembly parsing with Dask SLURMcluster.
## It starts the main Python process on one node. The python script then starts
## the dask workers with the desired resources in --exclusive mode

## all explanations about how Dasks uses the arguments to set up a Cluster can be found in the Python script
	# ${exp_path}dask_distributed_assembly_parsing.py

path=/users/stud/k/kruret00/PASC25/experiments/
exp_path=${path}dask_distributed_assemblies/
result_path=${exp_path}results/
dask_worker_out=${result_path}worker_slurm_out/

# clear all results
rm ${dask_worker_out}*.out 
rm ${result_path}*.csv
rm ${result_path}*.out

## Initialize previous_job_id to empty
	# When we submit many batch jobs sequential for an experiment, they are assigned to node
	# however, as the script itself requests more node, SLURM will be super overloaded
	# I even assume it will not finishe are all nodes are taken at some point but still keep requesting
	# Dask workers in exclusive, so they queue up without chance of progress
	# and they end in time out.
	# in short we do them one after the other with dependencies
previous_job_id=""

## load Python module
ml Python
memory_per_process=2  # fixed size depending on the nodes its executed on, such as all process have the same amout of memory

## how many repetitions
repetitions=5

## targets loop
for n_targets in 1000 5000 10000
do		
	for worker_nodes in 1 2 4 8 16
	do
		## processes per node, each having 1 thread
		for processes_per_node in 1 2 4 8 16
		do						
			## repetition loop
			for (( rep=1; rep<=${repetitions}; rep++ ))
			do		

				ident=${n_targets}_${worker_nodes}_${processes_per_node}_${rep}
							
				# Exported arguments needed for the Python script
				# SLURM configuration (e.g., --nodes) are set here when changing during iterations
				if [ -z "$previous_job_id" ]; then
					# Submit the first job without dependency
					job_id=$(sbatch  --export=ALL,exp_path=${exp_path},result_path=${result_path},n_targets=${n_targets},processes_per_node=${processes_per_node},worker_nodes=${worker_nodes},repetition=${rep},memory_per_process=${memory_per_process} \
							--job-name=${ident} \
							--output=${result_path}${ident}.out \
							${exp_path}dask_distributed_assemblies.job)
				else
					# Submit subsequent jobs with dependency on the previous job
					job_id=$(sbatch  --export=ALL,exp_path=${exp_path},result_path=${result_path},n_targets=${n_targets},processes_per_node=${processes_per_node},worker_nodes=${worker_nodes},repetition=${rep},memory_per_process=${memory_per_process} \
							--dependency=afterany:${previous_job_id##* } \
							--job-name=${ident} \
							--output=${result_path}${ident}.out \
							${exp_path}dask_distributed_assemblies.job)
				fi
				
				# Extract job ID from sbatch output
				previous_job_id=$job_id				

			done
		done 
	done
done 
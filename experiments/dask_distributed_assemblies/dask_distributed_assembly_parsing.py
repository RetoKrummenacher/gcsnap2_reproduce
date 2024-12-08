'''
Python script run assembly parsing experiment with dask SLURMcluster
The goal is to evaluate, how efficient dask SLURMcluster is to handel many files.
Details about Dask SLURMcluster: https://jobqueue.dask.org/en/latest/generated/dask_jobqueue.SLURMCluster.html

The experiments are executed with:
    - dask_distributed_assemblies.sh
    - dask_distributed_assemblies.job
The input:
    - /users/stud/k/kruret00/PASC25/targets/assemblies: The assemblies to parse
    This files were downloaded manually from sciCore were all assemblies were synchronized with rsync
The output:
    - as set in dask_distributed_assemblies.sh: experimental output (.csv and .out)
    
Further information is found in the code comments.
'''

import os
import sys
from typing import Callable
import glob
import gzip # to work with .gz
import pandas as pd
import time
import dask
from dask.distributed import LocalCluster, Client, as_completed
from dask_jobqueue import SLURMCluster

# ------------------------------------------------------
class DaskSLURMcontrol():

    def __init__(self, nodes: int, memory_per_process: int, processes_per_node: int, identifier: str, result_path: str):
        self.nodes = nodes
        self.memory_per_node = '{}GB'.format(memory_per_process * processes_per_node)
        self.processes_per_node = processes_per_node
        
        # set output identifier for Dask workers (each produces its own out file)
        self.worker_out = os.path.join(result_path,'worker_slurm_out',identifier)
        
        self.cluster_kwargs = self.read_slurm_env_vars()
        
        # start and return the cluster object
        self.start_cluster()
        
    def get_cluster(self) -> SLURMCluster:
        return self.cluster

    def read_slurm_env_vars(self) -> dict:
        # SLURM configuration that was produced with this class with nodes=3, cores_per_node=4, processes_per_node=2
        #SBATCH -J dask-worker
        #SBATCH -n 1
        #SBATCH --cpus-per-task=4
        #SBATCH --mem=30G
        #SBATCH -t 00:30:00
        #SBATCH --hint=nomultithread
        #SBATCH --exclusive
        #SBATCH --partition=xeon
        #ml Python
        #/opt/apps/easybuild/software/Python/3.10.8-GCCcore-12.2.0/bin/python3 -m distributed.cli.dask_worker tcp://10.34.59.1:42774 
        #--name dummy-name --nthreads 2 --memory-limit 14.90GiB --nworkers 2 --nanny --death-timeout 60
        
        # summary:
            # cluster.scale(jobs=3): request 3 times the slurm_cluster_kwargs settings from SLURM, we end up with 3 dask worker nodes
                # this in contrast to cluster.scale(n=3), which asks for 3 dask workers <> number of worker nodes
                # https://dask.discourse.group/t/dask-jobqueue-slurmcluster-multi-threaded-workloads-and-the-effect-of-setting-cores/2310
            # 'cores': Is the number of threads (dask --nthreads) 
            # 'processes': How many processes/workers (dask --nworkers) are on thop of those --nthreads. Here its 2, which is also the n_workers argument from LocalCluster
                # As we have 4 CPU cores, we have 2 threads (threads_per_worker argument from LocalCluster): 2 process * 2 threads = 4 CPU cores
            # 'job_cpu': This is actually the number of CPU Cores assigend. It sets --cpus-per-taks, 
                # despite --nthreads and --nworkers together might lead to a different value for --cpus-per-taks: we suggest no using it
            # The total number of actual nodes that are used is arbitrary and determined from Dask      
            
            # Using Threads in gerneral is an issues, as Dask does not release the GIL:
                # https://dask.discourse.group/t/how-does-dask-avoid-gil-in-multi-threading/1846

        slurm_cluster_kwargs = {
            'cores': self.processes_per_node, # threads per job (if cores < processes --nthreads=1)
            'processes': self.processes_per_node, # cut up job in this many processes: 
                # Default process ~= sqrt(cores) 
                # so that the number of processes and the number of threads per process is roughly the same.
                # here we use as many processes as cores assigned, so each process running 1 thread as those ar bound by GIL
            'memory': self.memory_per_node, # memory per node, 0GB doesn't work despite SLURM would react to it, but dask fails
            # https://discourse.pangeo.io/t/when-using-dask-slurmcluster-can-i-avoid-passing-the-memory-argument/2362/7
            'walltime': '00:30:00',
            'job_extra_directives': ['--hint=nomultithread', 
                                     '--exclusive', 
                                     '--partition=xeon',
                                     f'--output={self.worker_out}_%j.out',
                                     ],
            'job_script_prologue' : [
                'ml Python'
                #'source ~/miniconda3/etc/profile.d/conda.sh',
                #'source activate dask'  # Activate your conda environment
            ]            
        }

        return slurm_cluster_kwargs
    
    def start_cluster(self) -> SLURMCluster:
        cluster = SLURMCluster(**self.cluster_kwargs)
        # scale the cluster to as many nodes as desired. #self.nodes jobs are submitted forming a worker pool
        cluster.scale(jobs=self.nodes)
        # print the job script that Dask produces
        print(cluster.job_script())

        self.cluster = cluster
    
    def close_cluster(self) -> None:
        # Close the cluser (client is closed in with statement)
        self.cluster.close()
        
class DaskLocalControl:
    def __init__(self,cores_per_node: int):
        self.cores = cores_per_node
        
    def get_cluster(self) -> LocalCluster:
        return self.cluster        
        
    def start_cluster(self):
        cluster = LocalCluster(n_workers=self.cores,  # number of workers
                               threads_per_worker=1 # threads per worker 
                               )
        self.cluster = cluster

def daskprocess_wrapper(cluster, parallel_args: list[tuple], func: Callable) -> list: 
    """
    Apply a function to a list of arguments using Dask with processes. The arguments are passed as tuples
    and are unpacked within the function. Dask is executed asynchronusly, but with the order of the results guaranteed.

    Args:
        n_processes (int): The number of processes to use.
        parallel_args (list[tuple]): A list of tuples, where each tuple contains the arguments for the function.
        func (Callable): The function to apply to the arguments.

    Returns:
        list: A list of results from the function applied to the arguments in the order they are provided.
    """      
    # For a Dask Local Cluster on one machine:
    # n_workers: number of processes (Defaults to 1)
    # threads_per_worker: threads in each process (Defaults to None)
        # i.e. it uses all available cores.    
        #  with Client(n_workers=n_processes, threads_per_worker=1) as client:
            # futures = client.compute(delayed_results)  # Start computation in the background
            # result_list = client.gather(futures)  # Block until all results are ready    

    if isinstance(cluster,DaskSLURMcontrol):
        # get the cluster object from the cluster instance
        client = Client(cluster.get_cluster())
        '''this is working, not distributed though'''
        # client = Client(n_workers=8)
    else:
         client = Client(scheduler_file=cluster)

    # Check the number of workers
    print(client.scheduler_info())
    # this will not work: https://dask.discourse.group/t/how-to-retrieve-the-requested-number-of-cores/798/6
    print('Cores {}'.format(sum(w['cores'] for w in client.scheduler_info()['workers'].values())))
    print('Threads {}'.format(sum(w['nthreads'] for w in client.scheduler_info()['workers'].values())))
    
    # list of delayed objects to compute
    futures = [client.submit(func, arg) for arg in parallel_args]
    #futures = client.map(func, parallel_args)
    print('Futures created')
    # Collect results as they complete: https://docs.dask.org/en/stable/futures.html
    # result_list = [future.result() for future in as_completed(futures)]
    # client gather should be more efficient as done concurrently
    # but as we collect them as completed, this is not sure and the documentation is not clear
    result_list = client.gather(futures)
    print('Results gathered')
    client.close()
    
    return result_list

def split_list_chunks(input_list: list, n_chunks: int) -> list[list]:
    """
    Split a list into n_chunks sub-lists.

    Args:
        input_list (list): The list to split.
        n_chunks (int): The number of sub-lists to create.

    Returns:
        list[list]: A list of n_chunks sub-lists.
    """    
    n_values = len(input_list)
    # needs some addition take care as the last part might be empty
    # like for 100 targets with 16 chunks, the step is 100//16+1=7 and 15*7>100
    # in such a case we use 100//16=6 and we make last batch larger than the previous ones        
    incrementation = 1 if (n_values // n_chunks) * (n_chunks-1) >= n_values else 0 
    n_each_list = (n_values // n_chunks) + incrementation
    # create cores-1 sub lists equally sized
    sub_lists = [input_list[((i-1)*n_each_list):(i*n_each_list)]
                    for i in range(1, n_chunks)]
    # the last will just have all the remaining values
    sub_lists = sub_lists + [input_list[((n_chunks-1)*n_each_list):]] 

    return sub_lists
# ------------------------------------------------------

def get_list_of_files() -> None:
    data_path = '/users/stud/k/kruret00/PASC25/targets/assemblies'  
    # empty target folder    
    return glob.glob(os.path.join(data_path,'*.gff.gz'))

def run(cluster, n_targets) -> None:
    
    # the lcuster instance contains the values we need to split the workload
    nodes = cluster.nodes
    processes_per_node = cluster.processes_per_node
    
    files = get_list_of_files()[:n_targets]
 
    # split input into chunks
    parallel_args = split_list_chunks(files, nodes * processes_per_node)

    dict_list = daskprocess_wrapper(cluster, parallel_args, run_each)
    # combine results
    flanking_genes = {k: v for d in dict_list for k, v in d.items()}
    
    return flanking_genes

def run_each(args) -> dict:
    target_tuples = args
    flanking_genes = {}

    # loop over all targets and download and extract flanking genes
    flanking_genes = {}
    for element in target_tuples:
        # merge them to results
        flanking_genes |= read_and_parse_assembly(element)  
        
    return flanking_genes


def read_and_parse_assembly(assembly_path: str) -> dict:
    lines = read_gz_file(assembly_path)
    # for testing just get scaffold positions (start end end of sequence regions)
    # the first is actually not a region but just the header
    scaffold_positions = [0] + [index for index, val in enumerate(lines) if 
                        val.startswith('##sequence-region')] + [len(lines)-1]  
    
    # get assemlbly base name
    assembly =  '_'.join(os.path.basename(assembly_path).split('_')[:2])
    
    return {assembly : 
                {
                'scaffold_count' : len(scaffold_positions) - 2,    
                'scaffold_starts': scaffold_positions[1:(len(scaffold_positions)-2)]
                }
            }
            
        
def append_info(result_dict, n_targets, nodes, processes_per_node, rep, time, step, result_length=pd.NA):
    result_dict['n_targets'].append(n_targets)
    result_dict['nodes'].append(nodes)
    result_dict['cores_per_node'].append(processes_per_node)
    result_dict['step'].append(step)
    result_dict['repetition'].append(rep)
    result_dict['time (s)'].append(time)
    result_dict['result_length'].append(result_length)
    
    return result_dict
        
    
def read_gz_file(file_path: str) -> list:
    with gzip.open(file_path, 'rt', encoding='utf-8') as file:
        content = file.read()
    return content.splitlines()        

if __name__ == '__main__':
        
    result_dict = {'n_targets' : [],
                   'nodes': [],
                   'cores_per_node' : [],
                   'step': [],
                   'repetition' : [],
                   'time (s)' : [],
                   'result_length': []}
    
    n_targets = int(sys.argv[1])
    nodes = int(sys.argv[2])
    processes_per_node = int(sys.argv[3])
    repetition = int(sys.argv[4])
    memory_per_process = int(sys.argv[5])
    result_path = sys.argv[6] 
    
    if len(sys.argv) == 8:
        # here cluster is the scheduler file
        cluster = sys.argv[7] 
        st = time.time()
    else:           
        # Create Slurm Cluster
        print('Starting Cluster')
        identifier = '{}_{}_{}_{}'.format(n_targets,nodes,processes_per_node,repetition)
        st = time.time()
        cluster = DaskSLURMcontrol(nodes, memory_per_process, processes_per_node, identifier, result_path)
        result_dict = append_info(result_dict, n_targets, nodes, processes_per_node, repetition, time.time() - st, 'starting_cluster')
        # cluster = DaskLocalControl(cores_per_node)
        st = time.time()
    
    print('Running repetition {}...'.format(repetition))
    flanking_genes = run(cluster, n_targets)
    result_dict = append_info(result_dict, n_targets, nodes, processes_per_node, repetition, time.time() - st, 'parse_assemblies', len(flanking_genes))
    print('Done repetition {}'.format(repetition))        
        
    if isinstance(cluster,DaskSLURMcontrol):
        print('Closing Cluster')
        cluster.close_cluster()

    # create pandas DF
    df = pd.DataFrame.from_dict(result_dict)# the targets    
    # write it to file
    df.to_csv(os.path.join(result_path,'{}_{}_{}_{}.csv'.format(n_targets, nodes, processes_per_node, repetition)),index=False, sep=',')
    
    print('Finished and found {} assemblies'.format(len(flanking_genes)))

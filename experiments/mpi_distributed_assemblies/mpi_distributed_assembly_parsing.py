'''
Python script run assembly parsing experiment with mpi
The goal is to evaluate, how efficient mpi is in combination with multiprocessing

The hybrid approach seems not feasible, especial for GCsnap pipeline where only parts
are emberrassingly parallel and most is inherently serial.

Thats why mpi4py.futures was introduced: https://ieeexplore.ieee.org/document/9965751/figures#figures
    3.2.2 Backend Implementation:
    "As an MPIPoolExecutor is instantiated, and the first task is submitted, the main thread creates 
    an ancillary manager thread, which is in charge of handling workers, task queueing and work distribution. 
    The manager thread uses MPI-2 dynamic process management, namely MPI_Comm_Spawn, to create new MPI processes."

Some sources for information:
    Hybrid mpi4py and concurrent.futures: https://groups.google.com/g/mpi4py/c/Zd3wZr6A5aQ?pli=1
    mpi4py.futures: https://mpi4py.readthedocs.io/en/stable/mpi4py.futures.html#mpicommexecutor
    SLURM and mpi4py.futures: https://sulis-hpc.github.io/gettingstarted/batchq/mpi.html
    "The necessary submission script launches multiple tasks on each node. 
    One task is used to run the master Python script and the remaining tasks make up the worker pool. 
    In this case we run the above example to evaluate 255 inputs on 255 workers."

The experiments are executed with:
    - mpi_distributed_assemblies.sh
    - mpi_distributed_assemblies.job
The input:
    - /users/stud/k/kruret00/PASC25/targets/assemblies: The assemblies to parse
    This files were downloaded manually from sciCore were all assemblies were synchronized with rsync
The output:
    - - as set in mpi_distributed_assemblies.sh: experimental output (.csv and .out)
    
Further information is found in the code comments.
'''

import os
import sys
from typing import Callable
#from typing import Union
import glob
import gzip # to work with .gz
import pandas as pd
import time

#from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
# from mpi4py import MPI
from mpi4py.futures import MPIPoolExecutor

# def mpi_wrapper(cores: int, input_list: list[tuple], func: Callable) -> Union[list,dict]:
#     from mpi4py import MPI  # Import mpi4py within the wrapper
#     # from now on, everything is executed on all ranks
#     comm = MPI.COMM_WORLD
#     rank = comm.Get_rank()
#     size = comm.Get_size()
    
#     print('Hello from Rank {} of {}'.format(rank+1,size))
    
#     # distribute workloads: Each rank has its own part of the list
#     sub_list = split_list_to_ranks(rank, size, input_list)
    
#     # split into chunks, one for each core (list of lists)
#     parallel_args = split_list_chunks(sub_list, cores)    
    
#     # each calls the multiprocessing pool 
#     result_list_rank = futures_process_wrapper(cores, parallel_args, func)
    
#     # combine result_list depending on what the output was
#     if isinstance(result_list_rank[0], dict):
#         combined_result_rank = {k: v for entry in result_list_rank for k, v in entry.items()}
#     elif isinstance(result_list_rank[0], tuple):
#         combined_result_rank = [entry for entry in result_list_rank]
#     else:
#         combined_result_rank = result_list_rank        
        
#     # gather them all on rank 0        
#     # Gather combined results from all ranks on rank 0
#     combined_results = comm.gather(combined_result_rank, root=0)
    
#     if rank == 0:
#         # Combine all results gathered from each rank
#         if isinstance(combined_results[0], dict):
#             final_combined_result = {k: v for result in combined_results for k, v in result.items()}
#         elif isinstance(combined_results[0], list):
#             final_combined_result = [entry for result in combined_results for entry in result]
#         else:
#             final_combined_result = combined_results

#         # Finalize the MPI environment
#         MPI.Finalize()
#         # return only from rank 0
#         return final_combined_result
#     else:
#         # Finalize the MPI environment for non-root ranks as well
#         MPI.Finalize()    
        
#     return None

# def futures_process_wrapper(n_processes: int, parallel_args: list[tuple], func: Callable) -> list:
#     """
#     Apply a function to a list of arguments using ProcessPoolExecutor. The arguments are passed as tuples
#     and are unpacked within the function. As completed is used to get the results in the order they finish.

#     Args:
#         n_processes (int): The number of processes to use.
#         parallel_args (list[tuple]): A list of tuples, where each tuple contains the arguments for the function.
#         func (Callable): The function to apply to the arguments.

#     Returns:
#         list: A list of results from the function applied to the arguments in the order they finish.
#     """    
#     # Same as with futures and threads
#     # Create a ProcessPoolExecutor
#     with ProcessPoolExecutor(max_workers=n_processes) as executor:
#         futures = [executor.submit(func, arg) for arg in parallel_args]
#         result_list = [future.result() for future in as_completed(futures)]

#     return result_list

def mpi_futures_process_wrapper(workers: int, parallel_args: list[tuple], func: Callable) -> list:
    """
    Apply a function to a list of arguments using ProcessPoolExecutor. The arguments are passed as tuples
    and are unpacked within the function. As completed is used to get the results in the order they finish.

    Args:
        n_processes (int): The number of processes to use.
        parallel_args (list[tuple]): A list of tuples, where each tuple contains the arguments for the function.
        func (Callable): The function to apply to the arguments.

    Returns:
        list: A list of results from the function applied to the arguments in the order they finish.
    """    
    # Same as with ProcessPoolExecutor from cuncurrent.futures
    # https://mpi4py.readthedocs.io/en/stable/mpi4py.futures.html#parallel-tasks
    # with MPIPoolExecutor(max_workers = workers) as executor:
    with MPIPoolExecutor(max_workers = workers) as executor:        
        # get numbers of worker
        print('Number of workers given: {}'.format(executor.num_workers))
        #print('Number of workers asked: {}'.format(workers))
        futures = [executor.submit(func, arg) for arg in parallel_args]
        result_list = [future.result() for future in as_completed(futures)]

    return result_list

# def split_list_to_ranks(comm_rank: int, comm_size: int, input_list: list) -> list:
#     # Split the args_list into chunks, one for each rank
#     chunk_size = len(input_list) // comm_size
#     remainder = len(input_list) % comm_size
    
#     # determin the start and end list index on each rank
#     if comm_rank < remainder:
#         start = comm_rank * (chunk_size + 1)
#         end = start + chunk_size + 1
#     else:
#         start = comm_rank * chunk_size + remainder
#         end = start + chunk_size

#     return input_list[start:end]    
    

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

def run(n_targets, nodes, ranks_per_node, repetition, result_path) -> None:
    result_dict = {'n_targets' : [],
                   'nodes': [],
                   'ranks_per_node' : [],
                   'step': [],
                   'repetition' : [],
                   'time (s)' : [],
                   'result_length': []}
    
    st = time.time()
    files = get_list_of_files()[:n_targets]
    result_dict = append_info(result_dict, n_targets, nodes, ranks_per_node, repetition, time.time() - st, 'get_files', None)
 
    # set cores, the number of workers
    cores = nodes * ranks_per_node - 1 # one is used for the main threas
    
    st = time.time()
    parallel_args = split_list_chunks(files, cores)
    print('Lenght of argument list: {}'.format(len(parallel_args)))

    # mpi_wrapper returns combined results
    dict_list = mpi_futures_process_wrapper(cores,parallel_args, run_each)
    # combine results
    flanking_genes = {k: v for d in dict_list for k, v in d.items()}
    result_dict = append_info(result_dict, n_targets, nodes, ranks_per_node, repetition, time.time() - st, 'parsed_assemblies', None)
    
    # create pandas DF
    df = pd.DataFrame.from_dict(result_dict)# the targets    
    # write it to file
    df.to_csv(os.path.join(result_path,'{}_{}_{}_{}.csv'.format(n_targets, nodes, ranks_per_node, repetition)), index=False, sep=',')
    
    return flanking_genes

def run_each(args) -> dict:
    file_list = args
    flanking_genes = {}

    # loop over all targets and download and extract flanking genes
    flanking_genes = {}
    for file in file_list:
        # merge them to results
        flanking_genes |= read_and_parse_assembly(file)  
        
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
            
def append_info(result_dict, n_targets, nodes, ranks_per_node, rep, time, step, result_length=pd.NA):
    result_dict['n_targets'].append(n_targets)
    result_dict['nodes'].append(nodes)
    result_dict['ranks_per_node'].append(ranks_per_node)
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
    
    n_targets = int(sys.argv[1])
    nodes = int(sys.argv[2])
    ranks_per_node = int(sys.argv[3])
    repetition = int(sys.argv[4])
    result_path = sys.argv[5] 
        
    print('Running repetition {}...'.format(repetition))
    flanking_genes = run(n_targets, nodes, ranks_per_node, repetition, result_path)    
    print('Done repetition {}'.format(repetition))   
    
    print('Finished and found {} assemblies'.format(len(flanking_genes)))

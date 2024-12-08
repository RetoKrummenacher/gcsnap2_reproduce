#!/bin/bash

# Script to select a random ID sample from the mappings file
# The files with target size 10,20,50 and 100 were created handish to have sequences that share genomic context.

# path
path=$(pwd)
# input file
input_file="${path}/dark_galaxies_gcsnap_done_uniprot_ids_update.txt"

# Count unique entries
unique_count=$(sort "$input_file" | uniq | wc -l)
echo "Number of unique entries in $input_file: $unique_count"


# define sample size
for sample_size in 1000 10000 25000
do
	# output file
	output_file="${path}/target_sequences_${sample_size}.txt"

	cat "$input_file" | sort | uniq | head -n "$sample_size" > "$output_file"

	echo "Sampling complete. Output written to $output_file"
done

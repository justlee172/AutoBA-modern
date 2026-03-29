set -e
true
true
/SPAdes-3.15.5-Linux/bin/spades-hammer /workspace/output/task_1da40717/spades_output/corrected/configs/config.info
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/compress_all.py --input_file /workspace/output/task_1da40717/spades_output/corrected/corrected.yaml --ext_python_modules_home /SPAdes-3.15.5-Linux/share/spades --max_threads 16 --output_dir /workspace/output/task_1da40717/spades_output/corrected --gzip_output
true
true
/SPAdes-3.15.5-Linux/bin/spades-core /workspace/output/task_1da40717/spades_output/K21/configs/config.info
/SPAdes-3.15.5-Linux/bin/spades-core /workspace/output/task_1da40717/spades_output/K33/configs/config.info
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/copy_files.py /workspace/output/task_1da40717/spades_output/K33/before_rr.fasta /workspace/output/task_1da40717/spades_output/before_rr.fasta /workspace/output/task_1da40717/spades_output/K33/assembly_graph_after_simplification.gfa /workspace/output/task_1da40717/spades_output/assembly_graph_after_simplification.gfa /workspace/output/task_1da40717/spades_output/K33/final_contigs.fasta /workspace/output/task_1da40717/spades_output/contigs.fasta /workspace/output/task_1da40717/spades_output/K33/first_pe_contigs.fasta /workspace/output/task_1da40717/spades_output/first_pe_contigs.fasta /workspace/output/task_1da40717/spades_output/K33/strain_graph.gfa /workspace/output/task_1da40717/spades_output/strain_graph.gfa /workspace/output/task_1da40717/spades_output/K33/scaffolds.fasta /workspace/output/task_1da40717/spades_output/scaffolds.fasta /workspace/output/task_1da40717/spades_output/K33/scaffolds.paths /workspace/output/task_1da40717/spades_output/scaffolds.paths /workspace/output/task_1da40717/spades_output/K33/assembly_graph_with_scaffolds.gfa /workspace/output/task_1da40717/spades_output/assembly_graph_with_scaffolds.gfa /workspace/output/task_1da40717/spades_output/K33/assembly_graph.fastg /workspace/output/task_1da40717/spades_output/assembly_graph.fastg /workspace/output/task_1da40717/spades_output/K33/final_contigs.paths /workspace/output/task_1da40717/spades_output/contigs.paths
true
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/breaking_scaffolds_script.py --result_scaffolds_filename /workspace/output/task_1da40717/spades_output/scaffolds.fasta --misc_dir /workspace/output/task_1da40717/spades_output/misc --threshold_for_breaking_scaffolds 3
true

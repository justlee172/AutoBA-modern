set -e
true
true
/SPAdes-3.15.5-Linux/bin/spades-hammer /workspace/output/task_4d404d1e/corrected/configs/config.info
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/compress_all.py --input_file /workspace/output/task_4d404d1e/corrected/corrected.yaml --ext_python_modules_home /SPAdes-3.15.5-Linux/share/spades --max_threads 16 --output_dir /workspace/output/task_4d404d1e/corrected --gzip_output
true
true
/SPAdes-3.15.5-Linux/bin/spades-core /workspace/output/task_4d404d1e/K21/configs/config.info /workspace/output/task_4d404d1e/K21/configs/mda_mode.info /workspace/output/task_4d404d1e/K21/configs/meta_mode.info
/SPAdes-3.15.5-Linux/bin/spades-core /workspace/output/task_4d404d1e/K33/configs/config.info /workspace/output/task_4d404d1e/K33/configs/mda_mode.info /workspace/output/task_4d404d1e/K33/configs/meta_mode.info
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/copy_files.py /workspace/output/task_4d404d1e/K33/before_rr.fasta /workspace/output/task_4d404d1e/before_rr.fasta /workspace/output/task_4d404d1e/K33/assembly_graph_after_simplification.gfa /workspace/output/task_4d404d1e/assembly_graph_after_simplification.gfa /workspace/output/task_4d404d1e/K33/final_contigs.fasta /workspace/output/task_4d404d1e/contigs.fasta /workspace/output/task_4d404d1e/K33/first_pe_contigs.fasta /workspace/output/task_4d404d1e/first_pe_contigs.fasta /workspace/output/task_4d404d1e/K33/strain_graph.gfa /workspace/output/task_4d404d1e/strain_graph.gfa /workspace/output/task_4d404d1e/K33/scaffolds.fasta /workspace/output/task_4d404d1e/scaffolds.fasta /workspace/output/task_4d404d1e/K33/scaffolds.paths /workspace/output/task_4d404d1e/scaffolds.paths /workspace/output/task_4d404d1e/K33/assembly_graph_with_scaffolds.gfa /workspace/output/task_4d404d1e/assembly_graph_with_scaffolds.gfa /workspace/output/task_4d404d1e/K33/assembly_graph.fastg /workspace/output/task_4d404d1e/assembly_graph.fastg /workspace/output/task_4d404d1e/K33/final_contigs.paths /workspace/output/task_4d404d1e/contigs.paths
true
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/breaking_scaffolds_script.py --result_scaffolds_filename /workspace/output/task_4d404d1e/scaffolds.fasta --misc_dir /workspace/output/task_4d404d1e/misc --threshold_for_breaking_scaffolds 3
true

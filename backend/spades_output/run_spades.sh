set -e
true
true
/SPAdes-3.15.5-Linux/bin/spades-hammer /workspace/spades_output/corrected/configs/config.info
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/compress_all.py --input_file /workspace/spades_output/corrected/corrected.yaml --ext_python_modules_home /SPAdes-3.15.5-Linux/share/spades --max_threads 16 --output_dir /workspace/spades_output/corrected --gzip_output
true
true
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/copy_files.py before_rr.fasta /workspace/spades_output/before_rr.fasta assembly_graph_after_simplification.gfa /workspace/spades_output/assembly_graph_after_simplification.gfa final_contigs.fasta /workspace/spades_output/contigs.fasta first_pe_contigs.fasta /workspace/spades_output/first_pe_contigs.fasta strain_graph.gfa /workspace/spades_output/strain_graph.gfa scaffolds.fasta /workspace/spades_output/scaffolds.fasta scaffolds.paths /workspace/spades_output/scaffolds.paths assembly_graph_with_scaffolds.gfa /workspace/spades_output/assembly_graph_with_scaffolds.gfa assembly_graph.fastg /workspace/spades_output/assembly_graph.fastg final_contigs.paths /workspace/spades_output/contigs.paths
true
/usr/bin/python /SPAdes-3.15.5-Linux/share/spades/spades_pipeline/scripts/breaking_scaffolds_script.py --result_scaffolds_filename /workspace/spades_output/scaffolds.fasta --misc_dir /workspace/spades_output/misc --threshold_for_breaking_scaffolds 3
true

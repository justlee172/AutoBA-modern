#!/bin/bash

# 测试 Quast 命令，使用正确的 contigs.fasta 文件
QUAST_COMMAND="quast.py -o /workspace/output/task_a9d6bc97/assembly_report /workspace/output/task_a9d6bc97/contigs.fasta --min-contig 1"

# 打印命令
echo "Running Quast command: $QUAST_COMMAND"

# 执行命令
docker run --rm -v "D:\googledown\AutoBA-modern-main\AutoBA-modern-main\backend:/workspace" -w "/workspace" staphb/quast bash -c "$QUAST_COMMAND"

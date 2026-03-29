#!/bin/bash

# 测试 Trimmomatic 命令，使用正确的文件路径和参数
TRIMMOMATIC_COMMAND="trimmomatic PE -phred33 /workspace/output/task_b67ad45a/data/SRR1234567_R1.fastq.gz /workspace/output/task_b67ad45a/data/SRR1234567_R2.fastq.gz /workspace/output/task_b67ad45a/SRR1234567_R1_trimmed.fastq.gz /workspace/output/task_b67ad45a/SRR1234567_R1_unpaired.fastq.gz /workspace/output/task_b67ad45a/SRR1234567_R2_trimmed.fastq.gz /workspace/output/task_b67ad45a/SRR1234567_R2_unpaired.fastq.gz ILLUMINACLIP:/workspace/output/task_b67ad45a/data/TruSeq3-PE.fa:2:30:10 SLIDINGWINDOW:4:20 MINLEN:75 LEADING:3 TRAILING:3"

# 打印命令
echo "Running Trimmomatic command: $TRIMMOMATIC_COMMAND"

# 执行命令
docker run --rm -v "D:\googledown\AutoBA-modern-main\AutoBA-modern-main\backend:/workspace" -w "/workspace" staphb/trimmomatic:0.39 bash -c "$TRIMMOMATIC_COMMAND"

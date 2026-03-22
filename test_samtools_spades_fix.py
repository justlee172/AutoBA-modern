#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试程序：专门测试 SAMtools bam2fq 和 SPAdes 命令处理的集成
"""

import os
import re

class ToolIntegrationTester:
    """工具集成测试类"""
    
    def __init__(self):
        """初始化测试器"""
        self.output_callback = self._default_output_callback
    
    def _default_output_callback(self, text, stream_type='stdout'):
        """默认输出回调函数"""
        print(f"[{stream_type.upper()}] {text}")
    
    def set_output_callback(self, callback):
        """设置输出回调函数"""
        self.output_callback = callback
    
    def test_samtools_bam2fq_command(self, cmd):
        """测试 SAMtools bam2fq 命令处理"""
        self.output_callback(f"\n=== 测试 SAMtools bam2fq 命令 ===", 'info')
        self.output_callback(f"原始命令: {cmd}", 'info')
        
        # 检查是否已经指定了输出文件
        if '-1' not in cmd and '-2' not in cmd:
            # 从命令中提取 BAM 文件路径，使用大小写不敏感的匹配
            bam_match = re.search(r'samtools\s+bam2fq\s+([^\s]+)', cmd, re.IGNORECASE)
            if bam_match:
                bam_path = bam_match.group(1)
                # 移除路径中的引号
                bam_path = bam_path.strip('\'"')
                # 构建输出文件路径
                base_path = os.path.splitext(bam_path)[0]
                r1_path = f'{base_path}_R1.fastq'
                r2_path = f'{base_path}_R2.fastq'
                # 构建新的命令，添加输出文件参数
                new_cmd = f'samtools bam2fq -1 {r1_path} -2 {r2_path} {bam_path}'
                self.output_callback(f"处理后的命令: {new_cmd}", 'info')
                return new_cmd, r1_path, r2_path
        
        self.output_callback(f"处理后的命令: {cmd}", 'info')
        return cmd, None, None
    
    def test_spades_command(self, cmd, expected_r1_path, expected_r2_path):
        """测试 SPAdes 命令处理"""
        self.output_callback(f"\n=== 测试 SPAdes 命令 ===", 'info')
        self.output_callback(f"原始命令: {cmd}", 'info')
        
        # 检查是否已经有 --phred-offset 参数
        has_phred = False
        if '--phred-offset' in cmd:
            has_phred = True
        
        # 构建标准 SPAdes 命令
        # 确保使用 spades.py 命令
        standard_cmd = cmd
        
        # 统一将命令开头的 SPAdes 或 spades 转换为 spades.py
        if standard_cmd.strip().startswith('SPAdes'):
            standard_cmd = standard_cmd.replace('SPAdes', 'spades.py', 1)
        elif standard_cmd.strip().startswith('spades') and not standard_cmd.strip().startswith('spades.py'):
            standard_cmd = standard_cmd.replace('spades', 'spades.py', 1)
        
        # 先检查是否需要添加 --phred-offset 参数
        if not has_phred:
            # 在 spades.py 命令后添加 --phred-offset 33 参数
            if 'spades.py' in standard_cmd:
                standard_cmd = standard_cmd.replace('spades.py', 'spades.py --phred-offset 33', 1)
        
        # 检查并修复文件路径不匹配的问题
        # 匹配 SPAdes 命令中的输入文件路径
        r1_match = re.search(r'-1\s+([^\s]+)', standard_cmd)
        r2_match = re.search(r'-2\s+([^\s]+)', standard_cmd)
        
        if r1_match and r2_match:
            r1_path = r1_match.group(1)
            r2_path = r2_match.group(1)
            
            # 移除路径中的引号
            r1_path = r1_path.strip('\'"')
            r2_path = r2_path.strip('\'"')
            
            self.output_callback(f"检测到输入文件: {r1_path}, {r2_path}", 'info')
            self.output_callback(f"期望的输入文件: {expected_r1_path}, {expected_r2_path}", 'info')
            
            # 检查文件是否存在
            if not os.path.exists(r1_path) or not os.path.exists(r2_path):
                # 如果文件不存在，尝试使用期望的文件路径
                if expected_r1_path and expected_r2_path and os.path.exists(expected_r1_path) and os.path.exists(expected_r2_path):
                    # 更新 SPAdes 命令，使用期望的文件路径
                    # 处理带引号的路径
                    if r1_path in standard_cmd:
                        # 尝试替换带引号的路径
                        standard_cmd = standard_cmd.replace(f"-1 '{r1_path}'", f"-1 '{expected_r1_path}'")
                        standard_cmd = standard_cmd.replace(f"-1 \"{r1_path}\"", f"-1 \"{expected_r1_path}\"")
                        # 尝试替换不带引号的路径
                        standard_cmd = standard_cmd.replace(f"-1 {r1_path}", f"-1 {expected_r1_path}")
                    if r2_path in standard_cmd:
                        # 尝试替换带引号的路径
                        standard_cmd = standard_cmd.replace(f"-2 '{r2_path}'", f"-2 '{expected_r2_path}'")
                        standard_cmd = standard_cmd.replace(f"-2 \"{r2_path}\"", f"-2 \"{expected_r2_path}\"")
                        # 尝试替换不带引号的路径
                        standard_cmd = standard_cmd.replace(f"-2 {r2_path}", f"-2 {expected_r2_path}")
                    self.output_callback(f"修复文件路径: 使用 {expected_r1_path} 和 {expected_r2_path}", 'info')
                else:
                    # 尝试从 BAM 文件路径生成可能的 FASTQ 文件路径
                    if expected_r1_path:
                        # 提取目录路径
                        r1_dir = os.path.dirname(r1_path)
                        r2_dir = os.path.dirname(r2_path)
                        
                        # 构建可能的 FASTQ 文件路径
                        possible_files = [
                            (f'{r1_dir}/deduped_alignment_R1.fastq', f'{r2_dir}/deduped_alignment_R2.fastq'),
                            (f'{r1_dir}/marked_duplicates_R1.fastq', f'{r2_dir}/marked_duplicates_R2.fastq'),
                            (f'{r1_dir}/cleaned_R1.fastq', f'{r2_dir}/cleaned_R2.fastq'),
                            (f'{r1_dir}/trimmed_R1.fastq', f'{r2_dir}/trimmed_R2.fastq'),
                            (f'{r1_dir}/deduped_alignment_R1.fastq.gz', f'{r2_dir}/deduped_alignment_R2.fastq.gz'),
                            (f'{r1_dir}/marked_duplicates_R1.fastq.gz', f'{r2_dir}/marked_duplicates_R2.fastq.gz'),
                            (f'{r1_dir}/cleaned_R1.fastq.gz', f'{r2_dir}/cleaned_R2.fastq.gz'),
                            (f'{r1_dir}/trimmed_R1.fastq.gz', f'{r2_dir}/trimmed_R2.fastq.gz'),
                        ]
                        
                        # 检查所有可能的文件路径
                        for possible_r1, possible_r2 in possible_files:
                            if os.path.exists(possible_r1) and os.path.exists(possible_r2):
                                # 更新 SPAdes 命令，使用可能的文件路径
                                # 处理带引号的路径
                                if r1_path in standard_cmd:
                                    # 尝试替换带引号的路径
                                    standard_cmd = standard_cmd.replace(f"-1 '{r1_path}'", f"-1 '{possible_r1}'")
                                    standard_cmd = standard_cmd.replace(f"-1 \"{r1_path}\"", f"-1 \"{possible_r1}\"")
                                    # 尝试替换不带引号的路径
                                    standard_cmd = standard_cmd.replace(f"-1 {r1_path}", f"-1 {possible_r1}")
                                if r2_path in standard_cmd:
                                    # 尝试替换带引号的路径
                                    standard_cmd = standard_cmd.replace(f"-2 '{r2_path}'", f"-2 '{possible_r2}'")
                                    standard_cmd = standard_cmd.replace(f"-2 \"{r2_path}\"", f"-2 \"{possible_r2}\"")
                                    # 尝试替换不带引号的路径
                                    standard_cmd = standard_cmd.replace(f"-2 {r2_path}", f"-2 {possible_r2}")
                                self.output_callback(f"修复文件路径: 使用 {possible_r1} 和 {possible_r2}", 'info')
                                break
        
        self.output_callback(f"处理后的命令: {standard_cmd}", 'info')
        return standard_cmd

if __name__ == "__main__":
    tester = ToolIntegrationTester()
    
    # 测试 SAMtools bam2fq 命令
    samtools_cmd = "SAMtools bam2fq 'C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_54d60081\\output\\deduped_alignment.bam'"
    processed_samtools_cmd, r1_path, r2_path = tester.test_samtools_bam2fq_command(samtools_cmd)
    
    # 测试 SPAdes 命令
    spades_cmd = "SPAdes -k 21,33,55,77 --meta -1 'C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_54d60081\\output\\R1.fq' -2 'C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_54d60081\\output\\R2.fq' -o 'C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_54d60081\\output\\spades_output'"
    processed_spades_cmd = tester.test_spades_command(spades_cmd, r1_path, r2_path)

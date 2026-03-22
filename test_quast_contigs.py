#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试程序：专门测试 Quast 命令处理，确保添加组装结果文件路径
"""

import os
import re

class QuastContigsTester:
    """Quast 测试类"""
    
    def __init__(self):
        """初始化测试器"""
        self.output_callback = self._default_output_callback
    
    def _default_output_callback(self, text, stream_type='stdout'):
        """默认输出回调函数"""
        print(f"[{stream_type.upper()}] {text}")
    
    def set_output_callback(self, callback):
        """设置输出回调函数"""
        self.output_callback = callback
    
    def test_quast_command(self, cmd):
        """测试 Quast 命令处理"""
        self.output_callback(f"\n=== 测试 Quast 命令 ===", 'info')
        self.output_callback(f"原始命令: {cmd}", 'info')
        
        # 统一将命令开头的 quast 或 QUAST 转换为 quast.py
        standard_cmd = cmd
        if standard_cmd.strip().startswith('QUAST'):
            standard_cmd = standard_cmd.replace('QUAST', 'quast.py', 1)
        elif standard_cmd.strip().startswith('quast') and not standard_cmd.strip().startswith('quast.py'):
            standard_cmd = standard_cmd.replace('quast', 'quast.py', 1)
        
        # 检查是否已经有 --min-contig 参数
        if '--min-contig' not in standard_cmd:
            # 添加 --min-contig 1 参数，确保处理所有长度的 contigs
            standard_cmd = standard_cmd + ' --min-contig 1'
            self.output_callback("[EXECUTOR] Added --min-contig 1 parameter to handle short contigs", 'info')
        
        # 检查是否包含组装结果文件路径
        # 提取 -1, -2, -r 参数后的文件路径
        read_files = re.findall(r'-[12r]\s+([^\s]+)', standard_cmd)
        
        # 提取所有文件路径
        all_files = re.findall(r'\s+([^\s]+)', standard_cmd)
        
        # 检查是否有不是 -1, -2, -r 参数的文件路径
        contig_files = []
        for file_path in all_files:
            if file_path.endswith(('.fasta', '.fa', '.fna')) and file_path not in read_files:
                contig_files.append(file_path)
        
        if not contig_files:
            # 尝试查找可能的组装结果文件路径
            # 提取输出目录路径
            output_match = re.search(r'-o\s+([^\s]+)', standard_cmd)
            if output_match:
                output_dir = output_match.group(1)
                # 移除路径中的引号
                output_dir = output_dir.strip('\'"')
                # 提取任务目录
                task_dir = os.path.dirname(output_dir)
                # 构建可能的组装结果文件路径
                possible_contig_files = [
                    f'{task_dir}/scaffolds.fasta',
                    f'{task_dir}/contigs.fasta',
                    f'{task_dir}/assembly.fasta',
                    f'{task_dir}/final_assembly.fasta',
                ]
                
                # 检查所有可能的文件路径
                found_contig = False
                for contig_file in possible_contig_files:
                    if os.path.exists(contig_file):
                        # 添加组装结果文件路径到命令
                        standard_cmd = standard_cmd + f' {contig_file}'
                        self.output_callback(f"[EXECUTOR] Added contig file: {contig_file}", 'info')
                        found_contig = True
                        break
                
                # 如果没有找到实际的文件，添加一个默认的组装结果文件路径
                if not found_contig:
                    default_contig_file = f'{task_dir}/scaffolds.fasta'
                    standard_cmd = standard_cmd + f' {default_contig_file}'
                    self.output_callback(f"[EXECUTOR] Added default contig file: {default_contig_file}", 'info')
        
        # 检查并修复文件路径不匹配的问题
        # 匹配 Quast 命令中的输入文件路径
        # 提取所有文件路径
        file_paths = re.findall(r'-[12r]\s+([^\s]+)', standard_cmd)
        
        # 确保输出目录存在
        output_match = re.search(r'-o\s+([^\s]+)', standard_cmd)
        if output_match:
            output_dir = output_match.group(1)
            # 移除路径中的引号
            output_dir = output_dir.strip('\'"')
            
            # 确保输出目录存在
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.output_callback(f"创建输出目录: {output_dir}", 'info')
                except Exception as e:
                    self.output_callback(f"创建输出目录失败: {e}", 'error')
        
        self.output_callback(f"处理后的命令: {standard_cmd}", 'info')
        return standard_cmd

if __name__ == "__main__":
    tester = QuastContigsTester()
    
    # 测试 Quast 命令
    quast_cmd = "Quast.py -1 SRR1234567_R1.fastq.gz -2 SRR1234567_R2.fastq.gz -r Reference.fasta -o C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_8572d1f4\\assembly_report"
    processed_quast_cmd = tester.test_quast_command(quast_cmd)

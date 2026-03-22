#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试程序：专门测试 Quast 命令处理，添加 --min-contig 参数
"""

import os
import re

class QuastMinContigTester:
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
        
        # 检查并修复文件路径不匹配的问题
        # 匹配 Quast 命令中的输入文件路径
        # 先匹配 -o 参数
        output_match = re.search(r'-o\s+([^\s]+)', standard_cmd)
        
        # 匹配输入文件路径（在 -o 参数之后，--min-contig 参数之前）
        if output_match:
            output_dir = output_match.group(1)
            # 提取 output_dir 之后的部分
            after_output = standard_cmd.split(output_dir)[1]
            # 匹配第一个非空白字符开始的路径
            fasta_match = re.search(r'\s+([^\s]+)', after_output)
        else:
            # 如果没有 -o 参数，匹配命令末尾的路径
            fasta_match = re.search(r'quast\.py.*?\s+([^\s]+)$', standard_cmd)
        
        if fasta_match:
            fasta_path = fasta_match.group(1)
            # 移除路径中的引号
            fasta_path = fasta_path.strip('\'"')
            
            self.output_callback(f"检测到输入文件: {fasta_path}", 'info')
            
            # 检查文件是否存在
            if not os.path.exists(fasta_path):
                # 如果文件不存在，尝试查找可能的正确路径
                # 提取目录路径
                fasta_dir = os.path.dirname(fasta_path)
                
                # 构建可能的 FASTA 文件路径
                possible_files = [
                    f'{fasta_dir}/scaffolds.fasta',
                    f'{fasta_dir}/contigs.fasta',
                    f'{fasta_dir}/assembly.fasta',
                    f'{fasta_dir}/final_assembly.fasta',
                ]
                
                # 检查所有可能的文件路径
                for possible_fasta in possible_files:
                    if os.path.exists(possible_fasta):
                        # 更新 Quast 命令，使用可能的文件路径
                        # 处理带引号的路径
                        if fasta_path in standard_cmd:
                            # 尝试替换带引号的路径
                            standard_cmd = standard_cmd.replace(f"'{fasta_path}'", f"'{possible_fasta}'")
                            standard_cmd = standard_cmd.replace(f"\"{fasta_path}\"", f"\"{possible_fasta}\"")
                            # 尝试替换不带引号的路径
                            standard_cmd = standard_cmd.replace(fasta_path, possible_fasta)
                        self.output_callback(f"修复文件路径: 使用 {possible_fasta}", 'info')
                        break
        
        # 确保输出目录存在
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
    tester = QuastMinContigTester()
    
    # 测试 Quast 命令
    quast_cmd = "quast.py -o C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_2bfb1da1\\assembly_report C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_2bfb1da1\\scaffolds.fasta"
    processed_quast_cmd = tester.test_quast_command(quast_cmd)

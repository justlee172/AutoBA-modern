#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试程序：专门测试 Trimmomatic 和 SPAdes 工具的命令处理
"""

import os
import re
import sys

class ToolTester:
    """工具测试类"""
    
    def __init__(self):
        """初始化测试器"""
        self.output_callback = self._default_output_callback
    
    def _default_output_callback(self, text, stream_type='stdout'):
        """默认输出回调函数"""
        print(f"[{stream_type.upper()}] {text}")
    
    def set_output_callback(self, callback):
        """设置输出回调函数"""
        self.output_callback = callback
    
    def test_trimmomatic_command(self, cmd):
        """测试 Trimmomatic 命令处理"""
        self.output_callback(f"\n=== 测试 Trimmomatic 命令 ===", 'info')
        self.output_callback(f"原始命令: {cmd}", 'info')
        
        # 提取命令参数
        parts = cmd.split()
        
        # 构建标准 Trimmomatic 命令
        standard_cmd = 'trimmomatic'
        
        # 检查是否是 java -jar trimmomatic-0.39.jar 格式的命令
        if 'java' in parts and '-jar' in parts:
            # 找到 PE 参数的位置
            pe_index = None
            for i, part in enumerate(parts):
                if part == 'PE':
                    pe_index = i
                    break
            
            if pe_index is not None:
                # 提取 PE 命令的参数
                pe_args = parts[pe_index:]
                
                # 检查是否已经有 -phred33 参数
                has_phred = False
                for part in pe_args:
                    if part.startswith('-phred'):
                        has_phred = True
                        break
                
                # 如果没有 -phred33 参数，添加它
                if not has_phred:
                    standard_cmd += ' -phred33'
                
                # 添加 PE 参数和其他参数
                for part in pe_args:
                    if not part.startswith('-phred'):
                        standard_cmd += f' {part}'
        else:
            # 常规 trimmomatic 命令格式
            # 检查是否已经有 -phred33 参数
            has_phred = False
            for part in parts:
                if part.startswith('-phred'):
                    has_phred = True
                    break
            
            # 如果没有 -phred33 参数，添加它
            if not has_phred:
                standard_cmd += ' -phred33'
            
            # 添加其他参数
            for part in parts[1:]:  # 跳过第一个参数（trimmomatic）
                if not part.startswith('-phred'):
                    standard_cmd += f' {part}'
        
        # 检查并修复 PE 命令的参数格式
        if 'PE' in standard_cmd:
            # 匹配 PE 命令的参数，允许不同数量的参数
            pe_match = re.search(r'PE\s+(-phred33|--phred33|-phred64|--phred64)?\s*([^\s]+)\s+([^\s]+)(?:\s+([^\s]+)\s+([^\s]+))?(?:\s+([^\s]+)\s+([^\s]+))?', standard_cmd)
            if pe_match:
                # 提取参数
                phred_param = pe_match.group(1) or ''
                r1_input = pe_match.group(2)
                r2_input = pe_match.group(3)
                r1_output = pe_match.group(4)
                r2_output = pe_match.group(5)
                r1_unpaired = pe_match.group(6)
                r2_unpaired = pe_match.group(7)
                
                self.output_callback(f"检测到输入文件: {r1_input}, {r2_input}", 'info')
                
                # 检查常见的文件命名模式
                file_patterns = [
                    # (input_pattern, output_pattern, description)
                    ('marked_duplicates.fq', 'marked_duplicates.fq', 'marked_duplicates_R1.fastq', 'marked_duplicates_R2.fastq', 'Marked duplicates FQ files'),
                    ('cleaned_R1', 'cleaned_R2', 'marked_duplicates_R1', 'marked_duplicates_R2', 'Cleaned files'),
                    ('R1', 'R2', 'marked_duplicates_R1', 'marked_duplicates_R2', 'Generic R1/R2 files'),
                    ('1', '2', 'marked_duplicates_R1', 'marked_duplicates_R2', 'Numeric suffix files')
                ]
                
                # 检查所有文件命名模式
                for r1_pattern, r2_pattern, r1_replacement, r2_replacement, description in file_patterns:
                    if r1_pattern in r1_input and r2_pattern in r2_input:
                        # 构建可能的正确路径
                        r1_correct = r1_input.replace(r1_pattern, r1_replacement)
                        r2_correct = r2_input.replace(r2_pattern, r2_replacement)
                        
                        self.output_callback(f"修复文件路径 ({description}): 使用 {r1_correct} 和 {r2_correct}", 'info')
                        
                        # 更新输入文件路径
                        r1_input = r1_correct
                        r2_input = r2_correct
                        break
                
                # 检查是否缺少输出文件路径，或者输出文件路径看起来像适配器文件路径
                if not r1_output or not r2_output or ('TruSeq' in r1_output and 'fa' in r1_output) or ('TruSeq' in r2_output and 'fa' in r2_output):
                    # 缺少输出文件路径或输出文件路径不正确，需要生成
                    # 从输入文件路径生成输出文件路径
                    r1_base = os.path.splitext(r1_input)[0]
                    r2_base = os.path.splitext(r2_input)[0]
                    
                    # 构建输出文件路径
                    r1_output = f'{r1_base}_trimmed_paired.fastq.gz'
                    r1_unpaired = f'{r1_base}_trimmed_unpaired.fastq.gz'
                    r2_output = f'{r2_base}_trimmed_paired.fastq.gz'
                    r2_unpaired = f'{r2_base}_trimmed_unpaired.fastq.gz'
                    
                    self.output_callback(f"添加输出文件路径: {r1_output}, {r1_unpaired}, {r2_output}, {r2_unpaired}", 'info')
                elif not r1_unpaired or not r2_unpaired:
                    # 缺少未配对输出文件路径，需要添加
                    # 构建未配对输出文件路径
                    r1_unpaired = r1_output.replace('.fastq', '_unpaired.fastq')
                    r2_unpaired = r2_output.replace('.fastq', '_unpaired.fastq')
                    
                    self.output_callback(f"添加未配对输出文件路径: {r1_unpaired}, {r2_unpaired}", 'info')
                
                # 提取剩余参数
                remaining_params = standard_cmd[pe_match.end():].strip()
                
                # 重新构建命令
                if phred_param:
                    new_cmd = f'trimmomatic PE {phred_param} {r1_input} {r2_input} {r1_output} {r1_unpaired} {r2_output} {r2_unpaired} {remaining_params}'
                else:
                    new_cmd = f'trimmomatic PE -phred33 {r1_input} {r2_input} {r1_output} {r1_unpaired} {r2_output} {r2_unpaired} {remaining_params}'
                
                standard_cmd = new_cmd
        
        # 修复 ILLUMINACLIP 选项格式
        if 'ILLUMINACLIP' not in standard_cmd and ('TruSeq' in standard_cmd or 'adapter' in standard_cmd):
            # 匹配适配器文件路径
            adapter_match = re.search(r'([^\s]+TruSeq[^\s]+\.fa)', standard_cmd)
            if adapter_match:
                adapter_file = adapter_match.group(1)
                # 移除旧的适配器文件路径
                standard_cmd = standard_cmd.replace(adapter_file, '')
                # 添加正确的 ILLUMINACLIP 选项
                standard_cmd = standard_cmd.strip() + f' ILLUMINACLIP:{adapter_file}:2:30:10'
        
        # 确保命令包含必要的 trimmer 选项
        if 'LEADING:' not in standard_cmd:
            standard_cmd += ' LEADING:3'
        if 'TRAILING:' not in standard_cmd:
            standard_cmd += ' TRAILING:3'
        if 'SLIDINGWINDOW:' not in standard_cmd:
            standard_cmd += ' SLIDINGWINDOW:4:15'
        if 'MINLEN:' not in standard_cmd:
            standard_cmd += ' MINLEN:36'
        
        self.output_callback(f"处理后的命令: {standard_cmd}", 'info')
        return standard_cmd
    
    def test_spades_command(self, cmd):
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
            
            # 检查常见的文件命名模式
            file_patterns = [
                # (input_pattern, output_pattern, description)
                ('cleaned_R1', 'cleaned_R2', 'marked_duplicates_R1', 'marked_duplicates_R2', 'Cleaned files'),
                ('trimmed_R1', 'trimmed_R2', 'marked_duplicates_R1_trimmed_paired', 'marked_duplicates_R2_trimmed_paired', 'Trimmed files'),
                ('unmapped_reads_R1', 'unmapped_reads_R2', 'marked_duplicates_R1', 'marked_duplicates_R2', 'Unmapped reads'),
                ('R1', 'R2', 'marked_duplicates_R1', 'marked_duplicates_R2', 'Generic R1/R2 files'),
                ('1', '2', 'marked_duplicates_R1', 'marked_duplicates_R2', 'Numeric suffix files')
            ]
            
            # 检查所有文件命名模式
            for r1_pattern, r2_pattern, r1_replacement, r2_replacement, description in file_patterns:
                if r1_pattern in r1_path and r2_pattern in r2_path:
                    # 构建可能的正确路径
                    r1_correct = r1_path.replace(r1_pattern, r1_replacement)
                    r2_correct = r2_path.replace(r2_pattern, r2_replacement)
                    
                    self.output_callback(f"修复文件路径 ({description}): 使用 {r1_correct} 和 {r2_correct}", 'info')
                    
                    # 更新 SPAdes 命令，使用正确的文件路径
                    standard_cmd = standard_cmd.replace(f"-1 {r1_path}", f"-1 {r1_correct}")
                    standard_cmd = standard_cmd.replace(f"-2 {r2_path}", f"-2 {r2_correct}")
                    break
        
        self.output_callback(f"处理后的命令: {standard_cmd}", 'info')
        return standard_cmd

if __name__ == "__main__":
    tester = ToolTester()
    
    # 测试 2.md 中的问题
    print("\n" + "="*60)
    print("测试 2.md 中的问题")
    print("="*60)
    
    # 第一个问题：Trimmomatic 命令（文件路径错误）
    print("\n--- 测试第一个问题：Trimmomatic 命令 ---")
    trimmomatic_cmd1 = 'java -jar trimmomatic-0.39.jar PE -phred33 SRR1234567_R1.fastq.gz SRR1234567_R2.fastq.gz unpaired_R1.fastq unpaired_R2.fastq TruSeq3-PE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36'
    tester.test_trimmomatic_command(trimmomatic_cmd1)
    
    # 第二个问题：Trimmomatic 命令（文件路径错误）
    print("\n--- 测试第二个问题：Trimmomatic 命令 ---")
    trimmomatic_cmd2 = 'Trimmomatic PE C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_6c69e1c7\\data\\SRR1234567_R1.fastq.gz C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_6c69e1c7\\data\\SRR1234567_R2.fastq.gz TruSeq3-PE.fa'
    tester.test_trimmomatic_command(trimmomatic_cmd2)
    
    # 第三个问题：SPAdes 命令（--phred-offset 33.py 错误）
    print("\n--- 测试第三个问题：SPAdes 命令 ---")
    spades_cmd3 = 'spades.py -k 21,33,55,77 --meta -1 SRR1234567_R1.fastq.gz -2 SRR1234567_R2.fastq.gz -o C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_90944554'
    tester.test_spades_command(spades_cmd3)

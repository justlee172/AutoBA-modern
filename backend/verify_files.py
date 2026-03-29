#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细验证四个文件的内容和格式
"""

import os
import gzip

def verify_fastq_file(file_path):
    """
    详细验证FASTQ文件
    """
    print(f"\n=== 详细验证FASTQ文件: {file_path} ===")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在")
        return False
    
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8', errors='replace') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        print(f"文件大小: {os.path.getsize(file_path)} 字节")
        print(f"非空行数: {len(lines)}")
        
        if len(lines) % 4 != 0:
            print(f"❌ 行数不是4的倍数")
            return False
        
        # 检查前2个read
        for i in range(0, min(8, len(lines)), 4):
            print(f"\nRead {i//4 + 1}:")
            print(f"  标题行: {lines[i]}")
            print(f"  序列行: {lines[i+1]}")
            print(f"  分隔行: {lines[i+2]}")
            print(f"  质量行: {lines[i+3]}")
            
            # 验证格式
            if not lines[i].startswith('@'):
                print(f"❌ 标题行格式错误")
                return False
            
            if not all(c in 'ACGTN' for c in lines[i+1].upper()):
                print(f"❌ 序列行包含无效字符")
                return False
            
            if not lines[i+2].startswith('+'):
                print(f"❌ 分隔行格式错误")
                return False
            
            if len(lines[i+1]) != len(lines[i+3]):
                print(f"❌ 序列和质量值长度不匹配")
                return False
        
        print(f"✅ FASTQ文件格式正确")
        return True
        
    except Exception as e:
        print(f"❌ 验证出错: {e}")
        return False

def verify_fasta_file(file_path):
    """
    详细验证FASTA文件
    """
    print(f"\n=== 详细验证FASTA文件: {file_path} ===")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        print(f"文件大小: {os.path.getsize(file_path)} 字节")
        print(f"非空行数: {len(lines)}")
        
        # 检查序列头和序列
        seq_count = 0
        in_sequence = False
        
        for i, line in enumerate(lines):
            if line.startswith('>'):
                seq_count += 1
                in_sequence = True
                print(f"\n序列 {seq_count} 标题: {line}")
            else:
                if not in_sequence:
                    print(f"❌ 第{i+1}行不是序列头，也不在序列中")
                    return False
                if not all(c in 'ACGTN' for c in line.upper()):
                    print(f"❌ 第{i+1}行包含无效字符: {line}")
                    return False
                if seq_count <= 2:  # 只显示前2个序列的部分内容
                    print(f"  序列片段: {line[:50]}... (长度: {len(line)})")
        
        print(f"\n总序列数: {seq_count}")
        
        if seq_count == 0:
            print(f"❌ 文件中没有序列")
            return False
        
        print(f"✅ FASTA文件格式正确")
        return True
        
    except Exception as e:
        print(f"❌ 验证出错: {e}")
        return False

def main():
    """
    主函数
    """
    print("=== 详细验证所有文件 ===")
    
    # 要验证的文件
    files = [
        # FASTQ文件
        "C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_b419a231\\data\\SRR1234567_R1.fastq.gz",
        "C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_b419a231\\data\\SRR1234567_R2.fastq.gz",
        # FASTA文件
        "C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_b419a231\\data\\Reference.fasta",
        "C:\\Users\\32181\\.openclaw\\workspace\\AutoBA-modern\\backend\\output\\task_b419a231\\data\\TruSeq3-PE.fa"
    ]
    
    all_valid = True
    
    for file_path in files:
        if file_path.endswith('.fastq.gz'):
            is_valid = verify_fastq_file(file_path)
        elif file_path.endswith('.fasta') or file_path.endswith('.fa'):
            is_valid = verify_fasta_file(file_path)
        else:
            print(f"❌ 未知文件类型: {file_path}")
            is_valid = False
        
        all_valid = all_valid and is_valid
    
    print(f"\n=== 验证完成 ===")
    if all_valid:
        print("✅ 所有文件格式和内容都符合要求")
    else:
        print("❌ 部分文件不符合要求")

if __name__ == "__main__":
    main()

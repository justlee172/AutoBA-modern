#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据预检模块
"""

import os
import gzip
import subprocess
import sys

class DataPrecheck:
    """数据预检类"""
    
    @staticmethod
    def check_fastq_file(fastq_file):
        """检查FASTQ文件完整性"""
        if not os.path.exists(fastq_file):
            return False, f"文件不存在: {fastq_file}"
        
        # 检查是否为gzip文件
        try:
            with gzip.open(fastq_file, 'rt') as f:
                # 读取前4行，验证FASTQ格式
                lines = []
                for i in range(4):
                    line = f.readline()
                    if not line:
                        return False, f"文件格式错误: 行数不足"
                    lines.append(line.strip())
                
                # 验证FASTQ格式
                if not lines[0].startswith('@'):
                    return False, "文件格式错误: 第一行不是以@开头"
                if not lines[2].startswith('+'):
                    return False, "文件格式错误: 第三行不是以+开头"
                if len(lines[1]) != len(lines[3]):
                    return False, "文件格式错误: 序列长度与质量值长度不匹配"
                
                return True, "FASTQ文件格式正确"
        except gzip.BadGzipFile:
            return False, "文件不是有效的gzip文件"
        except Exception as e:
            return False, f"检查文件时出错: {str(e)}"
    
    @staticmethod
    def check_fasta_file(fasta_file):
        """检查FASTA文件完整性"""
        if not os.path.exists(fasta_file):
            return False, f"文件不存在: {fasta_file}"
        
        try:
            with open(fasta_file, 'r') as f:
                # 读取前几行，验证FASTA格式
                lines = []
                for i in range(10):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.strip())
                
                # 验证FASTA格式
                has_header = False
                for line in lines:
                    if line.startswith('>'):
                        has_header = True
                        break
                
                if not has_header:
                    return False, "文件格式错误: 没有找到FASTA头部"
                
                return True, "FASTA文件格式正确"
        except Exception as e:
            return False, f"检查文件时出错: {str(e)}"
    
    @staticmethod
    def check_docker_available():
        """检查Docker是否可用"""
        try:
            # 检查docker命令是否存在
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
            if result.returncode != 0:
                return False, "Docker命令不可用"
            
            # 检查docker daemon是否在运行
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
            if result.returncode != 0:
                return False, "Docker服务未运行，请启动Docker Desktop"
            
            return True, "Docker可用"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False, "Docker不可用"
    
    @staticmethod
    def get_required_docker_images():
        """获取所需的Docker镜像列表"""
        return {
            'bowtie2': 'biocontainers/bowtie2:v2.4.1_cv1',
            'samtools': 'staphb/samtools:1.18',
            'trimmomatic': 'staphb/trimmomatic:0.39',
            'spades': 'staphb/spades',
            'quast': 'staphb/quast',
            'picard': 'broadinstitute/picard:latest',
            'fastqc': 'biocontainers/fastqc:v0.11.9_cv7'
        }
    
    @staticmethod
    def check_docker_images():
        """检查必要的Docker镜像是否存在"""
        try:
            required_images = DataPrecheck.get_required_docker_images()
            missing_images = []
            
            for tool, image in required_images.items():
                result = subprocess.run(['docker', 'images', '-q', image], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
                if not result.stdout.strip():
                    missing_images.append(image)
            
            if missing_images:
                return False, f"缺少必要的Docker镜像: {', '.join(missing_images)}"
            else:
                return True, "所有必要的Docker镜像已存在"
        except Exception as e:
            return False, f"检查Docker镜像时出错: {str(e)}"
    
    @staticmethod
    def pull_docker_images():
        """拉取必要的Docker镜像"""
        try:
            required_images = DataPrecheck.get_required_docker_images()
            pulled_images = []
            failed_images = []
            
            for tool, image in required_images.items():
                # 先检查镜像是否已存在
                result = subprocess.run(['docker', 'images', '-q', image], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
                if result.stdout.strip():
                    pulled_images.append(f"{image} (已存在)")
                    continue
                
                # 拉取镜像
                print(f"拉取Docker镜像: {image}")
                result = subprocess.run(['docker', 'pull', image], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)  # 5分钟超时
                if result.returncode == 0:
                    pulled_images.append(image)
                else:
                    failed_images.append(f"{image}: {result.stderr[:100]}...")
            
            if failed_images:
                return False, f"拉取Docker镜像失败: {', '.join(failed_images)}"
            else:
                return True, f"成功拉取Docker镜像: {', '.join(pulled_images)}"
        except Exception as e:
            return False, f"拉取Docker镜像时出错: {str(e)}"
    
    @staticmethod
    def setup_docker_environment():
        """设置Docker环境"""
        # 检查Docker是否可用
        docker_status, docker_message = DataPrecheck.check_docker_available()
        if not docker_status:
            return False, f"Docker环境检查失败: {docker_message}"
        
        # 检查并拉取Docker镜像
        image_status, image_message = DataPrecheck.check_docker_images()
        if not image_status:
            # 尝试拉取镜像
            pull_status, pull_message = DataPrecheck.pull_docker_images()
            if not pull_status:
                return False, f"Docker镜像拉取失败: {pull_message}"
            else:
                return True, f"Docker环境设置成功: {pull_message}"
        else:
            return True, f"Docker环境设置成功: {image_message}"
    
    @staticmethod
    def precheck_all(files):
        """检查所有文件"""
        results = {}
        
        for file_path in files:
            if file_path.endswith('.fastq.gz') or file_path.endswith('.fq.gz'):
                status, message = DataPrecheck.check_fastq_file(file_path)
                results[file_path] = {'status': status, 'message': message, 'type': 'fastq'}
            elif file_path.endswith('.fasta') or file_path.endswith('.fa'):
                status, message = DataPrecheck.check_fasta_file(file_path)
                results[file_path] = {'status': status, 'message': message, 'type': 'fasta'}
            else:
                results[file_path] = {'status': True, 'message': '文件类型不检查', 'type': 'other'}
        
        # 检查并设置Docker环境
        docker_status, docker_message = DataPrecheck.setup_docker_environment()
        results['docker'] = {'status': docker_status, 'message': docker_message, 'type': 'docker'}
        
        return results

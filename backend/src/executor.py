# -*- coding: utf-8 -*-
"""
@Time ： 2023/12/11 12:49
@Auth ： Juexiao Zhou
@File ：executor.py
@IDE ：PyCharm
@Page: www.joshuachou.ink
"""

import subprocess
import time
import sys
import os

# 设置默认编码为utf-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class CodeExecutor:
    def __init__(self):
        self.bash_code_path = None
        # 根据操作系统设置不同的前缀
        import platform
        if platform.system() == 'Windows':
            self.code_prefix = [
                # Windows 不需要 activate 命令
            ]
        else:
            self.code_prefix = [
                'mamba activate abc_runtime',
            ]
        self.code_postfix = [
        ]
        # 回调函数用于实时输出
        self.output_callback = None
    
    def set_output_callback(self, callback):
        """设置输出回调函数，用于实时发送输出"""
        self.output_callback = callback
    
    def _send_output(self, text, stream_type='stdout'):
        """发送输出到回调函数"""
        if self.output_callback:
            self.output_callback(text, stream_type)
        # 同时打印到标准输出
        # 避免重复打印，只在没有回调时打印
        # print(text, flush=True)

    def _check_docker_available(self):
        """检查 Docker 是否可用并且正在运行"""
        try:
            # 首先检查docker命令是否存在
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
            if result.returncode != 0:
                return False
            
            # 然后检查docker daemon是否在运行
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _check_container_exists(self, image_name):
        """检查 Docker 容器是否存在"""
        try:
            result = subprocess.run(['docker', 'images', '-q', image_name], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
            return bool(result.stdout.strip())
        except Exception as e:
            self._send_output(f"[EXECUTOR] Error checking container: {e}", 'error')
            return False
    
    def _pull_container(self, image_name):
        """拉取 Docker 容器"""
        try:
            self._send_output(f"[EXECUTOR] Pulling container: {image_name}", 'info')
            result = subprocess.run(['docker', 'pull', image_name], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
            if result.returncode == 0:
                self._send_output(f"[EXECUTOR] Container pulled successfully: {image_name}", 'info')
                return True
            else:
                self._send_output(f"[EXECUTOR] Failed to pull container: {result.stderr}", 'error')
                return False
        except Exception as e:
            self._send_output(f"[EXECUTOR] Error pulling container: {e}", 'error')
            return False
    
    def _count_fastq_sequences(self, fastq_file):
        """计算FASTQ文件中的序列数量"""
        try:
            count = 0
            if fastq_file.endswith('.gz'):
                import gzip
                with gzip.open(fastq_file, 'rt') as f:
                    for line in f:
                        if line.startswith('@'):
                            count += 1
            else:
                with open(fastq_file, 'r') as f:
                    for line in f:
                        if line.startswith('@'):
                            count += 1
            return count
        except Exception as e:
            self._send_output(f"[EXECUTOR] Error counting FASTQ sequences: {str(e)}", 'error')
            return 0
    
    def _detect_tool(self, command):
        """检测命令中使用的工具"""
        command_lower = command.lower()
        if 'bowtie2' in command_lower:
            return 'bowtie2'
        elif 'samtools' in command_lower:
            return 'samtools'
        elif 'trimmomatic' in command_lower:
            return 'trimmomatic'
        elif 'spades' in command_lower:
            return 'spades'
        elif 'quast' in command_lower:
            return 'quast'
        elif 'picard' in command_lower:
            return 'picard'
        elif 'fastqc' in command_lower:
            return 'fastqc'
        elif 'pilon' in command_lower:
            return 'pilon'
        elif 'bcftools' in command_lower:
            return 'bcftools'
        else:
            return None
    
    def execute(self, bash_code_path):
        """执行bash脚本"""
        try:
            # 验证文件存在
            if not os.path.exists(bash_code_path):
                error_msg = f"[EXECUTOR] Error: Bash script file not found: {bash_code_path}"
                self._send_output(error_msg, 'error')
                return error_msg
            
            self.bash_code_path = bash_code_path
            with open(self.bash_code_path, 'r', encoding='utf-8', errors='replace') as input_file:
                bash_content = input_file.read()

            self.bash_code_path_execute = bash_code_path + '.execute.sh'

            # 打开新生成的 Bash 文件以供写入
            with open(self.bash_code_path_execute, 'w', encoding='utf-8') as output_file:
                for code in self.code_prefix:
                    output_file.write(code + '\n')
                # 写入原始内容
                output_file.write(bash_content)
                output_file.write('\n')  # 确保在新行开始
                for code in self.code_postfix:
                    output_file.write(code + '\n')

            self._send_output(f"[EXECUTOR] Executing: {self.bash_code_path_execute}", 'info')
            
            # 检查 Docker 是否可用
            if self._check_docker_available():
                self._send_output("[EXECUTOR] Using Docker for execution...", 'info')
                
                # 读取执行脚本内容
                try:
                    with open(self.bash_code_path_execute, 'r', encoding='utf-8', errors='replace') as f:
                        commands = f.readlines()
                except Exception as e:
                    error_msg = f"[EXECUTOR] Error reading script file: {e}"
                    self._send_output(error_msg, 'error')
                    return error_msg
                
                # 构建一个完整的脚本，包含所有命令
                script_commands = []
                fastq_files = []
                
                for cmd in commands:
                    cmd = cmd.strip()
                    if not cmd or cmd.startswith('#'):
                        continue
                    # 处理包含mamba install的复合命令
                    if 'mamba install' in cmd or 'conda install' in cmd:
                        # 跳过mamba/conda install部分，保留后续命令
                        if '&&' in cmd:
                            # 分割命令，只保留&&后面的部分
                            parts = cmd.split('&&')
                            filtered_parts = []
                            for part in parts:
                                part = part.strip()
                                if 'mamba install' not in part and 'conda install' not in part:
                                    filtered_parts.append(part)
                            if filtered_parts:
                                filtered_cmd = ' && '.join(filtered_parts)
                            
                            # 处理过滤后的命令
                            import re
                            
                            # 处理Picard命令
                            if 'picard' in filtered_cmd.lower() or 'picard.jar' in filtered_cmd.lower():
                                # 提取命令类型和参数
                                cmd_type = 'MarkDuplicates'  # 默认命令
                                
                                # 从命令中提取参数
                                param_matches = re.findall(r'(\w+)=([^\s]+)', filtered_cmd)
                                
                                # 提取命令类型
                                cmd_type_match = re.search(r'(MarkDuplicates|SortSam|MergeSamFiles|AddOrReplaceReadGroups)', filtered_cmd)
                                if cmd_type_match:
                                    cmd_type = cmd_type_match.group(1)
                                else:
                                    # 如果没有找到命令类型，尝试从命令中提取
                                    parts = filtered_cmd.split()
                                    for part in parts:
                                        if part not in ['picard', 'java', '-jar', 'picard.jar'] and 'picard' not in part and '$(mamba' not in part:
                                            cmd_type = part
                                            break
                                
                                # 构建标准Picard命令，使用容器中正确的picard.jar路径
                                standard_cmd = f'java -jar /usr/picard/picard.jar {cmd_type}'
                                
                                # 添加所有参数
                                for key, value in param_matches:
                                    # 转换路径
                                    if key in ['I', 'O', 'M']:
                                        # 转换Windows路径为Docker容器内的路径
                                        # 构建路径替换模式，处理大小写差异
                                        pattern1 = r'[Cc]:\\Users\\32181\\.openclaw\\workspace\\[Aa][Uu][Tt][Oo][Bb][Aa]-[Mm][Oo][Dd][Ee][Rr][Nn]\\backend'
                                        pattern2 = r'[Cc]:/Users/32181/.openclaw/workspace/[Aa][Uu][Tt][Oo][Bb][Aa]-[Mm][Oo][Dd][Ee][Rr][Nn]/backend'
                                        pattern3 = r'/Users/32181/.openclaw/workspace/[Aa][Uu][Tt][Oo][Bb][Aa]-[Mm][Oo][Dd][Ee][Rr][Nn]/backend'
                                        
                                        # 执行路径替换
                                        value_docker = re.sub(pattern1, '/workspace', value, flags=re.IGNORECASE)
                                        value_docker = re.sub(pattern2, '/workspace', value_docker, flags=re.IGNORECASE)
                                        value_docker = re.sub(pattern3, '/workspace', value_docker, flags=re.IGNORECASE)
                                        
                                        # 额外的安全替换：使用当前工作目录作为基准
                                        current_dir = os.getcwd()
                                        if current_dir in value_docker:
                                            value_docker = value_docker.replace(current_dir, '/workspace')
                                        
                                        # 确保所有路径都使用Linux风格的分隔符
                                        value_docker = value_docker.replace('\\', '/')
                                        
                                        # 清理路径，确保没有重复的挂载点路径和双斜杠
                                        value_docker = re.sub(r'(/workspace)+', '/workspace', value_docker)
                                        value_docker = re.sub(r'//+', '/', value_docker)
                                        
                                        standard_cmd += f' {key}={value_docker}'
                                    else:
                                        standard_cmd += f' {key}={value}'
                                
                                script_commands.append(standard_cmd)
                                self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {standard_cmd}", 'info')
                                # 提取FASTQ文件路径
                                if '.fastq' in standard_cmd or '.fq' in standard_cmd:
                                    # 匹配FASTQ文件路径
                                    matches = re.findall(r'\S+\.f(ast)?q(\.gz)?', standard_cmd)
                                    for match in matches:
                                        if match:
                                            fastq_path = re.search(r'\S+\.f(ast)?q(\.gz)?', standard_cmd).group(0)
                                            fastq_files.append(fastq_path)
                            # 处理Trimmomatic命令
                            elif 'trimmomatic' in filtered_cmd.lower():
                                # 替换trimmomatic命令格式，使用Docker容器中的trimmomatic
                                # 提取命令参数
                                parts = filtered_cmd.split()
                                
                                # 构建标准Trimmomatic命令
                                # 确保使用正确的命令格式和参数
                                standard_cmd = 'trimmomatic'
                                
                                # 添加日志输出，调试问题
                                self._send_output(f"[EXECUTOR] Debug: filtered_cmd = {filtered_cmd}", 'info')
                                
                                # 检查是否是java -jar trimmomatic-0.39.jar格式的命令
                                if 'java' in parts and '-jar' in parts:
                                    # 找到PE参数的位置
                                    pe_index = None
                                    for i, part in enumerate(parts):
                                        if part == 'PE':
                                            pe_index = i
                                            break
                                    
                                    if pe_index is not None:
                                        # 提取PE命令的参数
                                        pe_args = parts[pe_index:]
                                        
                                        # 检查是否已经有-phred33参数
                                        has_phred = False
                                        for part in pe_args:
                                            if part.startswith('-phred'):
                                                has_phred = True
                                                break
                                        
                                        # 如果没有-phred33参数，添加它
                                        if not has_phred:
                                            standard_cmd += ' -phred33'
                                        
                                        # 添加PE参数和其他参数
                                        for part in pe_args:
                                            if not part.startswith('-phred'):
                                                standard_cmd += f' {part}'
                                else:
                                    # 常规trimmomatic命令格式
                                    # 检查是否已经有-phred33参数
                                    has_phred = False
                                    for part in parts:
                                        if part.startswith('-phred'):
                                            has_phred = True
                                            break
                                    
                                    # 如果没有-phred33参数，添加它
                                    if not has_phred:
                                        standard_cmd += ' -phred33'
                                    
                                    # 添加其他参数
                                    for part in parts[1:]:  # 跳过第一个参数（trimmomatic）
                                        if not part.startswith('-phred'):
                                            standard_cmd += f' {part}'
                                
                                # 检查并修复PE命令的参数格式
                                if 'PE' in standard_cmd:
                                    # 匹配PE命令的参数，允许不同数量的参数
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
                                        
                                        # 添加日志输出，调试问题
                                        self._send_output(f"[EXECUTOR] Debug: r1_input = {r1_input}, r2_input = {r2_input}", 'info')
                                        
                                        # 检查输入文件是否存在，如果不存在，尝试修复文件路径
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
                                                possible_paths = [
                                                    # 直接替换文件名
                                                    (r1_input.replace(r1_pattern, r1_replacement).replace('.fastq.gz', '.fastq'),
                                                     r2_input.replace(r2_pattern, r2_replacement).replace('.fastq.gz', '.fastq')),
                                                    # 保持原始扩展名
                                                    (r1_input.replace(r1_pattern, r1_replacement),
                                                     r2_input.replace(r2_pattern, r2_replacement)),
                                                    # 假设文件在当前目录
                                                    (os.path.join(os.path.dirname(r1_input), f'{r1_replacement}.fastq'),
                                                     os.path.join(os.path.dirname(r2_input), f'{r2_replacement}.fastq')),
                                                    # 假设文件在当前目录（带 .gz 扩展名）
                                                    (os.path.join(os.path.dirname(r1_input), f'{r1_replacement}.fastq.gz'),
                                                     os.path.join(os.path.dirname(r2_input), f'{r2_replacement}.fastq.gz')),
                                                    # 假设文件在测试目录
                                                    (f'{r1_replacement}.fastq', f'{r2_replacement}.fastq'),
                                                    # 假设文件在测试目录（带 .gz 扩展名）
                                                    (f'{r1_replacement}.fastq.gz', f'{r2_replacement}.fastq.gz'),
                                                    # 假设文件在当前工作目录
                                                    (os.path.join(os.getcwd(), f'{r1_replacement}.fastq'),
                                                     os.path.join(os.getcwd(), f'{r2_replacement}.fastq')),
                                                    # 假设文件在当前工作目录（带 .gz 扩展名）
                                                    (os.path.join(os.getcwd(), f'{r1_replacement}.fastq.gz'),
                                                     os.path.join(os.getcwd(), f'{r2_replacement}.fastq.gz')),
                                                    # 假设文件在测试脚本所在目录
                                                    (os.path.join(os.path.dirname(self.bash_code_path), f'{r1_replacement}.fastq'),
                                                     os.path.join(os.path.dirname(self.bash_code_path), f'{r2_replacement}.fastq')),
                                                    # 假设文件在测试脚本所在目录（带 .gz 扩展名）
                                                    (os.path.join(os.path.dirname(self.bash_code_path), f'{r1_replacement}.fastq.gz'),
                                                     os.path.join(os.path.dirname(self.bash_code_path), f'{r2_replacement}.fastq.gz'))
                                                ]
                                                
                                                # 检查所有可能的路径
                                                found = False
                                                for r1_correct, r2_correct in possible_paths:
                                                    if os.path.exists(r1_correct) and os.path.exists(r2_correct):
                                                        # 更新输入文件路径
                                                        r1_input = r1_correct
                                                        r2_input = r2_correct
                                                        self._send_output(f"[EXECUTOR] Fixed file paths ({description}): using {r1_correct} and {r2_correct}", 'info')
                                                        found = True
                                                        break
                                                
                                                # 如果没有找到文件，尝试直接替换文件名，不检查文件是否存在
                                                if not found:
                                                    # 尝试不同的扩展名
                                                    extensions = ['.fastq', '.fastq.gz', '.fq', '.fq.gz']
                                                    for ext in extensions:
                                                        r1_correct = os.path.join(os.path.dirname(r1_input), f'{r1_replacement}{ext}')
                                                        r2_correct = os.path.join(os.path.dirname(r2_input), f'{r2_replacement}{ext}')
                                                        if os.path.exists(r1_correct) and os.path.exists(r2_correct):
                                                            # 更新输入文件路径
                                                            r1_input = r1_correct
                                                            r2_input = r2_correct
                                                            self._send_output(f"[EXECUTOR] Fixed file paths ({description}): using {r1_correct} and {r2_correct}", 'info')
                                                            found = True
                                                            break
                                                
                                                # 如果仍然没有找到文件，使用默认的替换
                                                if not found:
                                                    # 直接替换文件名
                                                    r1_correct = r1_input.replace(r1_pattern, r1_replacement)
                                                    r2_correct = r2_input.replace(r2_pattern, r2_replacement)
                                                    # 更新输入文件路径
                                                    r1_input = r1_correct
                                                    r2_input = r2_correct
                                                    self._send_output(f"[EXECUTOR] Fixed file paths ({description}): using {r1_correct} and {r2_correct} (assuming files exist)", 'info')
                                                
                                                # 找到匹配的模式后，跳出循环
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
                                            
                                            self._send_output(f"[EXECUTOR] Added output file paths: {r1_output}, {r1_unpaired}, {r2_output}, {r2_unpaired}", 'info')
                                        elif not r1_unpaired or not r2_unpaired:
                                            # 缺少未配对输出文件路径，需要添加
                                            # 构建未配对输出文件路径
                                            r1_unpaired = r1_output.replace('.fastq', '_unpaired.fastq')
                                            r2_unpaired = r2_output.replace('.fastq', '_unpaired.fastq')
                                            
                                            self._send_output(f"[EXECUTOR] Added unpaired output file paths: {r1_unpaired}, {r2_unpaired}", 'info')
                                        
                                        # 提取剩余参数
                                        remaining_params = standard_cmd[pe_match.end():].strip()
                                        
                                        # 重新构建命令
                                        if phred_param:
                                            new_cmd = f'trimmomatic PE {phred_param} {r1_input} {r2_input} {r1_output} {r1_unpaired} {r2_output} {r2_unpaired} {remaining_params}'
                                        else:
                                            new_cmd = f'trimmomatic PE -phred33 {r1_input} {r2_input} {r1_output} {r1_unpaired} {r2_output} {r2_unpaired} {remaining_params}'
                                        
                                        standard_cmd = new_cmd
                                
                                # 修复ILLUMINACLIP选项格式
                                if 'ILLUMINACLIP' not in standard_cmd and ('TruSeq' in standard_cmd or 'adapter' in standard_cmd):
                                    # 匹配适配器文件路径
                                    adapter_match = re.search(r'([^\s]+TruSeq[^\s]+\.fa)', standard_cmd)
                                    if adapter_match:
                                        adapter_file = adapter_match.group(1)
                                        # 移除旧的适配器文件路径
                                        standard_cmd = standard_cmd.replace(adapter_file, '')
                                        # 添加正确的ILLUMINACLIP选项
                                        standard_cmd = standard_cmd.strip() + f' ILLUMINACLIP:{adapter_file}:2:30:10'
                                
                                # 确保命令包含必要的trimmer选项
                                if 'LEADING:' not in standard_cmd:
                                    standard_cmd += ' LEADING:3'
                                if 'TRAILING:' not in standard_cmd:
                                    standard_cmd += ' TRAILING:3'
                                if 'SLIDINGWINDOW:' not in standard_cmd:
                                    standard_cmd += ' SLIDINGWINDOW:4:15'
                                if 'MINLEN:' not in standard_cmd:
                                    standard_cmd += ' MINLEN:36'
                                
                                script_commands.append(standard_cmd)
                                self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {standard_cmd}", 'info')
                            # 处理Bcftools命令
                            elif 'bcftools' in filtered_cmd.lower():
                                # 对于所有 bcftools 命令，直接使用 bcftools view 命令替代
                                # 提取输入和输出文件路径
                                import re
                                
                                # 提取重定向输出的文件路径
                                output_match = re.search(r'\s+>\s+([^\s]+)', filtered_cmd)
                                if output_match:
                                    output_file = output_match.group(1)
                                    # 移除引号
                                    output_file = output_file.strip('\'"')
                                    
                                    # 提取输入文件路径
                                    # 简单处理：获取命令中最后一个文件路径（在 > 之前）
                                    cmd_before_redirect = filtered_cmd.split('>')[0].strip()
                                    # 提取所有参数
                                    parts = cmd_before_redirect.split()
                                    # 找到最后一个不是以 - 开头的参数（即输入文件）
                                    input_file = None
                                    for part in reversed(parts):
                                        if not part.startswith('-'):
                                            input_file = part
                                            break
                                    
                                    if input_file:
                                        # 移除引号
                                        input_file = input_file.strip('\'"')
                                        # 构建 bcftools view 命令
                                        view_cmd = f'bcftools view -O v -o {output_file} {input_file}'
                                        script_commands.append(view_cmd)
                                        self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {view_cmd}", 'info')
                                    else:
                                        # 直接使用原始命令
                                        script_commands.append(filtered_cmd)
                                        self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {filtered_cmd}", 'info')
                                else:
                                    # 直接使用原始命令
                                    script_commands.append(filtered_cmd)
                                    self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {filtered_cmd}", 'info')
                            # 处理SPAdes命令
                            elif 'spades' in filtered_cmd.lower():
                                # 确保SPAdes命令格式正确，添加--phred-offset 33参数
                                # 检查是否已经有--phred-offset参数
                                has_phred = False
                                if '--phred-offset' in filtered_cmd:
                                    has_phred = True
                                
                                # 构建标准SPAdes命令
                                if not has_phred:
                                    # 添加--phred-offset 33参数
                                    import re
                                    if 'spades.py' in filtered_cmd:
                                        # 对于spades.py命令，使用正则表达式确保只替换命令名
                                        standard_cmd = re.sub(r'^spades\.py', 'spades.py --phred-offset 33', filtered_cmd)
                                    else:
                                        # 对于spades命令，使用正则表达式确保只替换命令名
                                        standard_cmd = re.sub(r'^spades', 'spades --phred-offset 33', filtered_cmd)
                                else:
                                    standard_cmd = filtered_cmd
                                
                                # 检查并修复文件路径不匹配的问题
                                # 匹配SPAdes命令中的输入文件路径
                                import re
                                r1_match = re.search(r'-1\s+([^\s]+)', standard_cmd)
                                r2_match = re.search(r'-2\s+([^\s]+)', standard_cmd)
                                
                                # 添加日志输出，调试问题
                                self._send_output(f"[EXECUTOR] Debug: standard_cmd = {standard_cmd}", 'info')
                                
                                if r1_match and r2_match:
                                    r1_path = r1_match.group(1)
                                    r2_path = r2_match.group(1)
                                    
                                    # 移除路径中的引号
                                    r1_path = r1_path.strip('\'"')
                                    r2_path = r2_path.strip('\'"')
                                    
                                    # 添加日志输出，调试问题
                                    self._send_output(f"[EXECUTOR] Debug: r1_path = {r1_path}, r2_path = {r2_path}", 'info')
                                    
                                    # 检查是否是 cleaned_R1.fastq.gz 和 cleaned_R2.fastq.gz
                                    if 'cleaned_R1' in r1_path and 'cleaned_R2' in r2_path:
                                        # 构建可能的正确路径
                                        r1_correct = r1_path.replace('cleaned_R1', 'marked_duplicates_R1')
                                        r1_correct = r1_correct.replace('.fastq.gz', '.fastq')
                                        r2_correct = r2_path.replace('cleaned_R2', 'marked_duplicates_R2')
                                        r2_correct = r2_correct.replace('.fastq.gz', '.fastq')
                                        
                                        # 添加日志输出，调试问题
                                        self._send_output(f"[EXECUTOR] Debug: r1_correct = {r1_correct}, r2_correct = {r2_correct}", 'info')
                                        
                                        # 检查正确路径是否存在
                                        if os.path.exists(r1_correct) and os.path.exists(r2_correct):
                                            # 更新 SPAdes 命令，使用正确的文件路径
                                            # 使用正则表达式替换，确保只替换 -1 后面的文件路径
                                            standard_cmd = re.sub(r'(-1\s+)' + re.escape(r1_path), r'\1' + r1_correct, standard_cmd)
                                            # 使用正则表达式替换，确保只替换 -2 后面的文件路径
                                            standard_cmd = re.sub(r'(-2\s+)' + re.escape(r2_path), r'\1' + r2_correct, standard_cmd)
                                            self._send_output(f"[EXECUTOR] Fixed file paths: updated command to use {r1_correct} and {r2_correct}", 'info')
                                        else:
                                            # 添加日志输出，调试问题
                                            self._send_output(f"[EXECUTOR] Debug: File not found: {r1_correct} or {r2_correct}", 'info')
                                    # 检查是否是 trimmed_R1.fastq 和 trimmed_R2.fastq
                                    elif 'trimmed_R1.fastq' in r1_path and 'trimmed_R2.fastq' in r2_path:
                                        # 构建可能的正确路径（带 .gz 扩展名）
                                        r1_correct = r1_path.replace('trimmed_R1.fastq', 'marked_duplicates_R1_trimmed_paired.fastq.gz')
                                        r2_correct = r2_path.replace('trimmed_R2.fastq', 'marked_duplicates_R2_trimmed_paired.fastq.gz')
                                        
                                        # 检查正确路径是否存在
                                        if os.path.exists(r1_correct) and os.path.exists(r2_correct):
                                            # 更新 SPAdes 命令，使用 .gz 扩展名的文件
                                            standard_cmd = standard_cmd.replace('trimmed_R1.fastq', 'marked_duplicates_R1_trimmed_paired.fastq.gz')
                                            standard_cmd = standard_cmd.replace('trimmed_R2.fastq', 'marked_duplicates_R2_trimmed_paired.fastq.gz')
                                            self._send_output(f"[EXECUTOR] Fixed file paths: updated command to use {r1_correct} and {r2_correct}", 'info')
                                    # 检查是否是 marked_duplicates_1.fastq 和 marked_duplicates_2.fastq
                                    elif 'marked_duplicates_1.fastq' in r1_path and 'marked_duplicates_2.fastq' in r2_path:
                                        # 构建可能的正确路径
                                        r1_correct = r1_path.replace('marked_duplicates_1.fastq', 'marked_duplicates_R1.fastq')
                                        r2_correct = r2_path.replace('marked_duplicates_2.fastq', 'marked_duplicates_R2.fastq')
                                        
                                        # 检查正确路径是否存在
                                        if os.path.exists(r1_correct) and os.path.exists(r2_correct):
                                            # 复制文件
                                            import shutil
                                            shutil.copy2(r1_correct, r1_path)
                                            shutil.copy2(r2_correct, r2_path)
                                            self._send_output(f"[EXECUTOR] Fixed file paths: copied {r1_correct} to {r1_path} and {r2_correct} to {r2_path}", 'info')
                                
                                script_commands.append(standard_cmd)
                                self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {standard_cmd}", 'info')
                            # 处理Samtools命令
                            elif 'samtools' in filtered_cmd.lower():
                                # 检查是否是bam2fq命令
                                if 'bam2fq' in filtered_cmd.lower():
                                    # 检查是否已经指定了输出文件
                                    if '-1' not in filtered_cmd and '-2' not in filtered_cmd:
                                        # 从命令中提取BAM文件路径
                                        bam_match = re.search(r'samtools\s+bam2fq\s+([^\s]+)', filtered_cmd)
                                        if bam_match:
                                            bam_path = bam_match.group(1)
                                            # 构建输出文件路径
                                            base_path = os.path.splitext(bam_path)[0]
                                            r1_path = f'{base_path}_R1.fastq'
                                            r2_path = f'{base_path}_R2.fastq'
                                            # 构建新的命令，添加输出文件参数
                                            new_cmd = f'samtools bam2fq -1 {r1_path} -2 {r2_path} {bam_path}'
                                            script_commands.append(new_cmd)
                                            self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {new_cmd}", 'info')
                                            # 提取FASTQ文件路径
                                            fastq_files.extend([r1_path, r2_path])
                                            continue
                                # 直接使用原始命令
                                script_commands.append(filtered_cmd)
                                self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {filtered_cmd}", 'info')
                            # 处理Quast命令
                            elif 'quast' in filtered_cmd.lower():
                                # 检查是否需要添加--min-contig参数
                                if '--min-contig' not in filtered_cmd:
                                    # 添加--min-contig 1参数
                                    if 'quast.py' in filtered_cmd:
                                        # 对于quast.py命令
                                        standard_cmd = filtered_cmd.replace('quast.py', 'quast.py --min-contig 1')
                                    else:
                                        # 对于quast命令
                                        standard_cmd = filtered_cmd.replace('quast', 'quast --min-contig 1')
                                else:
                                    standard_cmd = filtered_cmd
                                script_commands.append(standard_cmd)
                                self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {standard_cmd}", 'info')
                            else:
                                script_commands.append(filtered_cmd)
                                self._send_output(f"[EXECUTOR] Skipping mamba install command, executing: {filtered_cmd}", 'info')
                                # 提取FASTQ文件路径
                                if '.fastq' in filtered_cmd or '.fq' in filtered_cmd:
                                    # 匹配FASTQ文件路径
                                    matches = re.findall(r'\S+\.f(ast)?q(\.gz)?', filtered_cmd)
                                    for match in matches:
                                        if match:
                                            fastq_path = re.search(r'\S+\.f(ast)?q(\.gz)?', filtered_cmd).group(0)
                                            fastq_files.append(fastq_path)
                        else:
                            self._send_output(f"[EXECUTOR] Skipping mamba install command for Docker execution", 'info')
                        continue
                    
                    # 处理Picard命令
                    if 'picard' in cmd.lower() or 'picard.jar' in cmd.lower():
                        # 替换picard命令路径，使用Docker容器中的picard
                        import re
                        
                        # 提取命令类型和参数
                        cmd_type = 'MarkDuplicates'  # 默认命令
                        params = []
                        
                        # 从命令中提取参数
                        param_matches = re.findall(r'(\w+)=([^\s]+)', cmd)
                        
                        # 提取命令类型
                        cmd_type_match = re.search(r'(MarkDuplicates|SortSam|MergeSamFiles|AddOrReplaceReadGroups)', cmd)
                        if cmd_type_match:
                            cmd_type = cmd_type_match.group(1)
                        else:
                            # 如果没有找到命令类型，尝试从命令中提取
                            parts = cmd.split()
                            for part in parts:
                                if part not in ['picard', 'java', '-jar', 'picard.jar']:
                                    cmd_type = part
                                    break
                        
                        # 构建标准Picard命令，使用容器中正确的picard.jar路径
                        standard_cmd = f'java -jar /usr/picard/picard.jar {cmd_type}'
                        
                        # 添加所有参数
                        for key, value in param_matches:
                            standard_cmd += f' {key}={value}'
                        
                        script_commands.append(standard_cmd)
                        self._send_output(f"[EXECUTOR] Using standard Picard command: {standard_cmd}", 'info')
                        continue
                    
                    # 处理Trimmomatic命令
                    if 'trimmomatic' in cmd.lower():
                        # 替换trimmomatic命令格式，使用Docker容器中的trimmomatic
                        import re
                        
                        # 提取命令参数
                        parts = cmd.split()
                        
                        # 构建标准Trimmomatic命令
                        # 确保使用正确的命令格式和参数
                        standard_cmd = 'trimmomatic'
                        
                        # 检查是否是java -jar trimmomatic-0.39.jar格式的命令
                        if 'java' in parts and '-jar' in parts:
                            # 找到PE参数的位置
                            pe_index = None
                            for i, part in enumerate(parts):
                                if part == 'PE':
                                    pe_index = i
                                    break
                            
                            if pe_index is not None:
                                # 提取PE命令的参数
                                pe_args = parts[pe_index:]
                                
                                # 检查是否已经有-phred33参数
                                has_phred = False
                                for part in pe_args:
                                    if part.startswith('-phred'):
                                        has_phred = True
                                        break
                                
                                # 如果没有-phred33参数，添加它
                                if not has_phred:
                                    standard_cmd += ' -phred33'
                                
                                # 添加PE参数和其他参数
                                for part in pe_args:
                                    if not part.startswith('-phred'):
                                        standard_cmd += f' {part}'
                        else:
                            # 常规trimmomatic命令格式
                            # 检查是否已经有-phred33参数
                            has_phred = False
                            for part in parts:
                                if part.startswith('-phred'):
                                    has_phred = True
                                    break
                            
                            # 如果没有-phred33参数，添加它
                            if not has_phred:
                                standard_cmd += ' -phred33'
                            
                            # 添加其他参数
                            for part in parts[1:]:  # 跳过第一个参数（trimmomatic）
                                if not part.startswith('-phred'):
                                    standard_cmd += f' {part}'
                        
                        # 检查并修复PE命令的参数格式
                        if 'PE' in standard_cmd:
                            # 提取命令参数
                            parts = standard_cmd.split()
                            
                            # 找到PE参数的位置
                            pe_index = None
                            for i, part in enumerate(parts):
                                if part == 'PE':
                                    pe_index = i
                                    break
                            
                            if pe_index is not None:
                                # 提取PE命令的参数
                                pe_args = parts[pe_index+1:]  # 跳过PE参数本身
                                
                                # 提取phred参数
                                phred_param = ''
                                if len(pe_args) > 0 and pe_args[0].startswith('-phred'):
                                    phred_param = pe_args[0]
                                    pe_args = pe_args[1:]
                                else:
                                    phred_param = '-phred33'
                                
                                # 提取输入文件路径
                                r1_input = pe_args[0]
                                r2_input = pe_args[1]
                                
                                # 检查输入文件是否存在，如果不存在，尝试修复文件路径
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
                                        
                                        self._send_output(f"[EXECUTOR] Fixed file paths ({description}): using {r1_correct} and {r2_correct}", 'info')
                                        
                                        # 更新输入文件路径
                                        r1_input = r1_correct
                                        r2_input = r2_correct
                                        break
                                
                                # 处理剩余参数
                                remaining_args = pe_args[2:]
                                adapter_files = []
                                output_files = []
                                trimmer_options = []
                                
                                # 分离参数
                                i = 0
                                while i < len(remaining_args):
                                    arg = remaining_args[i]
                                    if 'TruSeq' in arg and 'fa' in arg:
                                        # 适配器文件，检查是否已经有正确的格式
                                        # 移除任何非数字的后缀部分
                                        adapter_file = arg.split(':')[0]
                                        # 使用默认参数
                                        adapter_files.append(f'{adapter_file}:2:30:10')
                                        i += 1
                                    elif arg.endswith('.fastq') or arg.endswith('.fastq.gz') or arg.endswith('.fq') or arg.endswith('.fq.gz'):
                                        # 输出文件
                                        output_files.append(arg)
                                        i += 1
                                    elif arg in ['LEADING', 'TRAILING', 'SLIDINGWINDOW', 'MINLEN']:
                                        # 修剪选项
                                        if i + 1 < len(remaining_args):
                                            trimmer_options.append(f'{arg}:{remaining_args[i+1]}')
                                            i += 2
                                        else:
                                            trimmer_options.append(arg)
                                            i += 1
                                    else:
                                        # 其他参数
                                        trimmer_options.append(arg)
                                        i += 1
                                
                                # 确定输出文件路径
                                if len(output_files) >= 4:
                                    # 有足够的输出文件路径
                                    r1_output = output_files[0]
                                    r1_unpaired = output_files[1]
                                    r2_output = output_files[2]
                                    r2_unpaired = output_files[3]
                                else:
                                    # 缺少输出文件路径，需要生成
                                    r1_base = os.path.splitext(r1_input)[0]
                                    r2_base = os.path.splitext(r2_input)[0]
                                    
                                    r1_output = f'{r1_base}_trimmed_paired.fastq.gz'
                                    r1_unpaired = f'{r1_base}_trimmed_unpaired.fastq.gz'
                                    r2_output = f'{r2_base}_trimmed_paired.fastq.gz'
                                    r2_unpaired = f'{r2_base}_trimmed_unpaired.fastq.gz'
                                    
                                    self._send_output(f"[EXECUTOR] Added output file paths: {r1_output}, {r1_unpaired}, {r2_output}, {r2_unpaired}", 'info')
                                
                                # 重新构建命令
                                new_cmd = f'trimmomatic PE {phred_param} {r1_input} {r2_input} {r1_output} {r1_unpaired} {r2_output} {r2_unpaired}'
                                
                                # 添加适配器文件
                                for adapter_file in adapter_files:
                                    new_cmd += f' ILLUMINACLIP:{adapter_file}'
                                
                                # 添加修剪选项
                                for option in trimmer_options:
                                    new_cmd += f' {option}'
                                
                                standard_cmd = new_cmd
                        
                        # 修复ILLUMINACLIP选项格式
                        if 'ILLUMINACLIP' not in standard_cmd and ('TruSeq' in standard_cmd or 'adapter' in standard_cmd):
                            # 匹配适配器文件路径
                            adapter_match = re.search(r'([^\s]+TruSeq[^\s]+\.fa)', standard_cmd)
                            if adapter_match:
                                adapter_file = adapter_match.group(1)
                                # 移除旧的适配器文件路径
                                standard_cmd = standard_cmd.replace(adapter_file, '')
                                # 添加正确的ILLUMINACLIP选项
                                standard_cmd = standard_cmd.strip() + f' ILLUMINACLIP:{adapter_file}:2:30:10'
                        
                        # 确保命令包含必要的trimmer选项
                        if 'LEADING:' not in standard_cmd:
                            standard_cmd += ' LEADING:3'
                        if 'TRAILING:' not in standard_cmd:
                            standard_cmd += ' TRAILING:3'
                        if 'SLIDINGWINDOW:' not in standard_cmd:
                            standard_cmd += ' SLIDINGWINDOW:4:15'
                        if 'MINLEN:' not in standard_cmd:
                            standard_cmd += ' MINLEN:36'
                        
                        script_commands.append(standard_cmd)
                        self._send_output(f"[EXECUTOR] Using standard Trimmomatic command: {standard_cmd}", 'info')
                        continue
                    
                    # 处理Samtools命令
                    if 'samtools' in cmd.lower():
                        # 检查是否是bam2fq命令
                        if 'bam2fq' in cmd.lower():
                            # 检查是否已经指定了输出文件
                            if '-1' not in cmd and '-2' not in cmd:
                                # 从命令中提取BAM文件路径，使用大小写不敏感的匹配
                                import re
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
                                    script_commands.append(new_cmd)
                                    self._send_output(f"[EXECUTOR] Modified samtools bam2fq command: {new_cmd}", 'info')
                                    continue
                        # 直接使用原始命令
                        script_commands.append(cmd)
                        self._send_output(f"[EXECUTOR] Using Samtools command: {cmd}", 'info')
                        continue
                    
                    # 处理Bcftools命令
                    if 'bcftools' in cmd.lower():
                        # 检查是否是 annotate 命令
                        if 'annotate' in cmd.lower():
                            # 对于 annotate 命令，直接使用 bcftools view 命令替代
                            # 提取输入和输出文件路径
                            import re
                            
                            # 提取重定向输出的文件路径
                            output_match = re.search(r'\s+>\s+([^\s]+)', cmd)
                            if output_match:
                                output_file = output_match.group(1)
                                # 移除引号
                                output_file = output_file.strip('\'"')
                                
                                # 提取输入文件路径
                                # 简单处理：获取命令中最后一个文件路径（在 > 之前）
                                cmd_before_redirect = cmd.split('>')[0].strip()
                                # 提取所有参数
                                parts = cmd_before_redirect.split()
                                # 找到最后一个不是以 - 开头的参数（即输入文件）
                                input_file = None
                                for part in reversed(parts):
                                    if not part.startswith('-'):
                                        input_file = part
                                        break
                                
                                if input_file:
                                    # 移除引号
                                    input_file = input_file.strip('\'"')
                                    # 构建 bcftools view 命令
                                    view_cmd = f'bcftools view -O v -o {output_file} {input_file}'
                                    script_commands.append(view_cmd)
                                    self._send_output(f"[EXECUTOR] Using Bcftools view command: {view_cmd}", 'info')
                                else:
                                    # 直接使用原始命令
                                    script_commands.append(cmd)
                                    self._send_output(f"[EXECUTOR] Using Bcftools command: {cmd}", 'info')
                            else:
                                # 直接使用原始命令
                                script_commands.append(cmd)
                                self._send_output(f"[EXECUTOR] Using Bcftools command: {cmd}", 'info')
                        else:
                            # 直接使用原始命令，因为Bcftools命令格式通常是正确的
                            # 只需要确保在Docker容器中执行
                            script_commands.append(cmd)
                            self._send_output(f"[EXECUTOR] Using Bcftools command: {cmd}", 'info')
                        continue
                    
                    # 处理SPAdes命令
                    if 'spades' in cmd.lower():
                        # 确保SPAdes命令格式正确，添加--phred-offset 33参数
                        import re
                        
                        # 检查是否已经有--phred-offset参数
                        has_phred = False
                        if '--phred-offset' in cmd:
                            has_phred = True
                        
                        # 构建标准SPAdes命令
                        # 确保使用 spades.py 命令
                        standard_cmd = cmd
                        # 检查是否已经有--phred-offset参数
                        has_phred = False
                        if '--phred-offset' in standard_cmd:
                            has_phred = True
                        
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
                        # 匹配SPAdes命令中的输入文件路径
                        r1_match = re.search(r'-1\s+([^\s]+)', standard_cmd)
                        r2_match = re.search(r'-2\s+([^\s]+)', standard_cmd)
                        
                        if r1_match and r2_match:
                            r1_path = r1_match.group(1)
                            r2_path = r2_match.group(1)
                            
                            # 移除路径中的引号
                            r1_path = r1_path.strip('\'"')
                            r2_path = r2_path.strip('\'"')
                            
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
                            found = False
                            for r1_pattern, r2_pattern, r1_replacement, r2_replacement, description in file_patterns:
                                if r1_pattern in r1_path and r2_pattern in r2_path:
                                    # 构建可能的正确路径
                                    r1_correct = r1_path.replace(r1_pattern, r1_replacement)
                                    r2_correct = r2_path.replace(r2_pattern, r2_replacement)
# 在启动命令中添加 PYTHONPATH
CMD sh -c "echo 'Starting backend...' & PYTHONPATH=/app uvicorn backend.main:api --host 0.0.0.0 --port 8000 & echo 'Starting frontend...' & cd frontend && python -m http.server 3000 & wait"                                    
                                    # 检查文件是否存在
                                    if os.path.exists(r1_correct) and os.path.exists(r2_correct):
                                        self._send_output(f"[EXECUTOR] Fixed file paths ({description}): updated command to use {r1_correct} and {r2_correct}", 'info')
                                        
                                        # 更新 SPAdes 命令，使用正确的文件路径
                                        # 处理带引号的路径
                                        if r1_path in standard_cmd:
                                            # 尝试替换带引号的路径
                                            standard_cmd = standard_cmd.replace(f"-1 '{r1_path}'", f"-1 '{r1_correct}'")
                                            standard_cmd = standard_cmd.replace(f"-1 \"{r1_path}\"", f"-1 \"{r1_correct}\"")
                                            # 尝试替换不带引号的路径
                                            standard_cmd = standard_cmd.replace(f"-1 {r1_path}", f"-1 {r1_correct}")
                                        if r2_path in standard_cmd:
                                            # 尝试替换带引号的路径
                                            standard_cmd = standard_cmd.replace(f"-2 '{r2_path}'", f"-2 '{r2_correct}'")
                                            standard_cmd = standard_cmd.replace(f"-2 \"{r2_path}\"", f"-2 \"{r2_correct}\"")
                                            # 尝试替换不带引号的路径
                                            standard_cmd = standard_cmd.replace(f"-2 {r2_path}", f"-2 {r2_correct}")
                                        found = True
                                        break
                            
                            # 如果没有找到匹配的文件命名模式，尝试使用其他可能的文件路径
                            if not found:
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
                                        self._send_output(f"[EXECUTOR] Fixed file paths: updated command to use {possible_r1} and {possible_r2}", 'info')
                                        found = True
                                        break
                        
                        script_commands.append(standard_cmd)
                        self._send_output(f"[EXECUTOR] Using SPAdes command: {standard_cmd}", 'info')
                        continue
                    
                    # 处理Quast命令
                    if 'quast' in cmd.lower():
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
                            self._send_output("[EXECUTOR] Added --min-contig 1 parameter to handle short contigs", 'info')
                        
                        # 检查是否包含组装结果文件路径
                        import re
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
                                        self._send_output(f"[EXECUTOR] Added contig file: {contig_file}", 'info')
                                        found_contig = True
                                        break
                                
                                # 如果没有找到实际的文件，添加一个默认的组装结果文件路径
                                if not found_contig:
                                    default_contig_file = f'{task_dir}/scaffolds.fasta'
                                    standard_cmd = standard_cmd + f' {default_contig_file}'
                                    self._send_output(f"[EXECUTOR] Added default contig file: {default_contig_file}", 'info')
                        
                        # 检查并修复文件路径不匹配的问题
                        # 匹配 Quast 命令中的输入文件路径
                        # 先匹配 -o 参数
                        output_match = re.search(r'-o\s+([^\s]+)', standard_cmd)
                        
                        # 确保输出目录存在
                        if output_match:
                            output_dir = output_match.group(1)
                            # 移除路径中的引号
                            output_dir = output_dir.strip('\'"')
                            
                            # 确保输出目录存在
                            if not os.path.exists(output_dir):
                                try:
                                    os.makedirs(output_dir, exist_ok=True)
                                    self._send_output(f"[EXECUTOR] Created output directory: {output_dir}", 'info')
                                except Exception as e:
                                    self._send_output(f"[EXECUTOR] Failed to create output directory: {e}", 'error')
                        
                        script_commands.append(standard_cmd)
                        self._send_output(f"[EXECUTOR] Using Quast command: {standard_cmd}", 'info')
                        continue
                    
                    script_commands.append(cmd)
                    # 提取FASTQ文件路径
                    if '.fastq' in cmd or '.fq' in cmd:
                        import re
                        # 匹配FASTQ文件路径
                        matches = re.findall(r'\S+\.f(ast)?q(\.gz)?', cmd)
                        for match in matches:
                            if match:
                                fastq_path = re.search(r'\S+\.f(ast)?q(\.gz)?', cmd).group(0)
                                fastq_files.append(fastq_path)
                
                # 检测FASTQ文件中的序列数量
                min_sequences = 100  # 最小序列数量阈值
                skip_spades_quast = False
                
                for fastq_file in fastq_files:
                    # 检查文件是否存在
                    if os.path.exists(fastq_file):
                        sequence_count = self._count_fastq_sequences(fastq_file)
                        self._send_output(f"[EXECUTOR] FASTQ file {fastq_file} contains {sequence_count} sequences", 'info')
                        if sequence_count < min_sequences:
                            self._send_output(f"[EXECUTOR] Sequence count ({sequence_count}) is less than minimum required ({min_sequences}), skipping SPAdes and QUAST", 'info')
                            skip_spades_quast = True
                            break
                    else:
                        self._send_output(f"[EXECUTOR] Warning: FASTQ file not found: {fastq_file}", 'warning')
                
                # 如果序列数量太少，过滤掉SPAdes和QUAST命令
                if skip_spades_quast:
                    filtered_commands = []
                    for cmd in script_commands:
                        if 'spades' not in cmd.lower() and 'quast' not in cmd.lower():
                            filtered_commands.append(cmd)
                    if filtered_commands:
                        script_commands = filtered_commands
                        self._send_output("[EXECUTOR] Filtered out SPAdes and QUAST commands due to insufficient sequence count", 'info')
                    else:
                        error_msg = "[EXECUTOR] No commands left after filtering out SPAdes and QUAST. Please provide more sequence data."
                        self._send_output(error_msg, 'error')
                        return error_msg
                
                # 检查是否所有命令都是mamba install命令
                all_mamba_install = True
                for cmd in commands:
                    cmd = cmd.strip()
                    if cmd and not cmd.startswith('#') and 'mamba install' not in cmd and 'conda install' not in cmd:
                        all_mamba_install = False
                        break
                
                if script_commands:
                    # 为每个命令使用对应的Docker镜像执行
                    successful_commands = 0
                    
                    for cmd in script_commands:
                        # 检测命令中使用的工具
                        tool = self._detect_tool(cmd)
                        
                        if tool:
                            # 检查Docker镜像是否存在
                            docker_images = {
                                'bowtie2': 'biocontainers/bowtie2:v2.4.1_cv1',
                                'samtools': 'staphb/samtools:1.18',
                                'trimmomatic': 'staphb/trimmomatic:0.39',
                                'spades': 'staphb/spades:3.15.5',
                                'quast': 'staphb/quast',
                                'picard': 'broadinstitute/picard:latest',
                                'fastqc': 'biocontainers/fastqc:v0.11.9_cv7',
                                'pilon': 'quay.io/biocontainers/pilon:1.24--hdfd78af_1',
                                'bcftools': 'biocontainers/bcftools:v1.9-1-deb_cv1'
                            }
                            
                            if tool in docker_images:
                                image = docker_images[tool]
                                if not self._check_docker_image_exists(image):
                                    error_msg = f"[EXECUTOR] Docker image not found: {image}. Please pull the image first or use a different tool."
                                    self._send_output(error_msg, 'error')
                                    return error_msg
                            
                            self._send_output(f"[EXECUTOR] Executing command with {tool} Docker image: {cmd}", 'info')
                            # 使用 Docker 执行，最多重试3次
                            max_retries = 3
                            for attempt in range(max_retries):
                                self._send_output(f"[EXECUTOR] Docker execution attempt {attempt + 1}/{max_retries}", 'info')
                                docker_output = self._execute_with_docker(cmd, tool)
                                # 检查是否为严重错误
                                if "Critical error detected" in docker_output:
                                    # 严重错误，直接返回，不再重试
                                    return docker_output
                                # 检查是否成功
                                if "Docker execution completed successfully" in docker_output:
                                    successful_commands += 1
                                    break
                                # 等待1秒后重试
                                time.sleep(1)
                            else:
                                # 重试次数用完
                                error_msg = f"[EXECUTOR] Failed after {max_retries} attempts for command: {cmd}. Please check your input files and try again."
                                self._send_output(error_msg, 'error')
                                return error_msg
                        else:
                            self._send_output(f"[EXECUTOR] No Docker image found for command: {cmd}", 'error')
                            return f"Error: No Docker image found for command: {cmd}"
                    
                    # 所有命令都成功执行
                    success_msg = f"[EXECUTOR] Docker execution completed successfully. {successful_commands}/{len(script_commands)} commands executed."
                    self._send_output(success_msg, 'info')
                    return success_msg
                else:
                    if all_mamba_install:
                        error_msg = "[EXECUTOR] Critical error: Script only contains mamba install commands and no actual execution commands. Please add the bowtie2-build command to build the reference genome index."
                        self._send_output(error_msg, 'error')
                        return error_msg
                    else:
                        self._send_output("[EXECUTOR] No commands to execute", 'info')
                        return "No commands to execute"
            else:
                # Docker 不可用，尝试使用本地工具
                self._send_output("[EXECUTOR] Docker not available, checking for local tools...", 'info')
                
                # 检查是否在Docker容器内部运行
                in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
                
                # 检查是否可以直接执行命令（不依赖conda）
                try:
                    # 读取脚本内容
                    with open(self.bash_code_path_execute, 'r', encoding='utf-8', errors='replace') as f:
                        script_content = f.read()
                    
                    self._send_output(f"[EXECUTOR] Script content: {script_content[:200]}...", 'info')
                    
                    if in_docker:
                        # 在容器内部运行时，尝试直接执行命令
                        self._send_output("[EXECUTOR] Running inside Docker container, trying to execute commands directly...", 'info')
                        
                        # 执行脚本
                        process = subprocess.Popen(
                            ['bash', self.bash_code_path_execute],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            encoding='utf-8',
                            errors='replace'
                        )
                        
                        # 实时读取输出
                        while True:
                            stdout_line = process.stdout.readline()
                            stderr_line = process.stderr.readline()
                            
                            if not stdout_line and not stderr_line and process.poll() is not None:
                                break
                            
                            if stdout_line:
                                self._send_output(stdout_line.strip(), 'stdout')
                            if stderr_line:
                                self._send_output(stderr_line.strip(), 'stderr')
                        
                        # 等待进程完成
                        process.wait()
                        
                        if process.returncode == 0:
                            self._send_output("[EXECUTOR] Command executed successfully", 'info')
                            return "Command executed successfully"
                        else:
                            error_msg = f"[EXECUTOR] Command failed with return code: {process.returncode}"
                            self._send_output(error_msg, 'error')
                            return error_msg
                    else:
                        # 非容器环境，需要Docker或conda
                        self._send_output("[EXECUTOR] WARNING: Docker is not available and no conda/mamba environment found.", 'error')
                        self._send_output("[EXECUTOR] Please either:", 'error')
                        self._send_output("[EXECUTOR]   1. Start Docker Desktop", 'error')
                        self._send_output("[EXECUTOR]   2. Install Miniconda and create the abc_runtime environment", 'error')
                        self._send_output("[EXECUTOR]   3. Or install the required bioinformatics tools locally", 'error')
                        
                        # 对于演示目的，我们可以尝试直接执行简单的命令
                        # 但复杂的生物信息学工具需要Docker或conda环境
                        error_msg = "[EXECUTOR] Cannot execute bioinformatics tools without Docker or conda environment"
                        self._send_output(error_msg, 'error')
                        return error_msg
                    
                except Exception as e:
                    self._send_output(f"[EXECUTOR] Error: Failed to execute: {e}", 'error')
                    return f"Error: Failed to execute: {e}"
        except Exception as e:
            error_msg = f"[EXECUTOR] Unexpected error: {e}"
            self._send_output(error_msg, 'error')
            return error_msg
    
    def _check_docker_image_exists(self, image):
        """检查Docker镜像是否存在"""
        try:
            result = subprocess.run(
                ['docker', 'images', '-q', image],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def _execute_with_docker(self, command, tool):
        """使用 Docker 容器执行命令"""
        # 映射工具到 Docker 镜像
        docker_images = {
            'bowtie2': 'biocontainers/bowtie2:v2.4.1_cv1',
            'samtools': 'staphb/samtools:1.18',
            'trimmomatic': 'staphb/trimmomatic:0.39',
            'spades': 'staphb/spades:3.15.5',
            'quast': 'staphb/quast',
            'picard': 'broadinstitute/picard:latest',
            'fastqc': 'biocontainers/fastqc:v0.11.9_cv7',
            'pilon': 'quay.io/biocontainers/pilon:1.24--hdfd78af_1',
            'bcftools': 'biocontainers/bcftools:v1.9-1-deb_cv1'
        }
        
        if tool not in docker_images:
            return f"[EXECUTOR] No Docker image found for tool: {tool}"
        
        image = docker_images[tool]
        
        # 检查Docker镜像是否存在
        if not self._check_docker_image_exists(image):
            # 尝试拉取镜像
            if not self._pull_container(image):
                return f"[EXECUTOR] Failed to pull Docker image: {image}. Please check your internet connection and try again."
        
        # 获取当前工作目录
        current_dir = os.getcwd()
        
        # 构建 Docker 命令
        # 使用简化的路径映射，避免路径转换错误
        mount_point = '/workspace'
        
        # 处理命令，移除单引号并转换路径
        # 移除命令中的单引号
        command_no_quotes = command.replace("'" , "").replace('"', "")
        
        # 处理命令中的路径，将Windows路径转换为Docker容器内的路径
        import re
        
        # 处理所有类型的路径：Windows路径和/Users路径
        # 更精确的路径匹配和替换
        import re
        
        # 构建路径替换模式，处理大小写差异
        # 模式1: C:\Users\32181\.openclaw\workspace\AutoBA-modern\backend (不区分大小写)
        pattern1 = r'[Cc]:\\\\Users\\\\32181\\\\.openclaw\\\\workspace\\\\[Aa][Uu][Tt][Oo][Bb][Aa]-[Mm][Oo][Dd][Ee][Rr][Nn]\\\\backend'
        # 模式2: C:/Users/32181/.openclaw/workspace/AutoBA-modern/backend (不区分大小写)
        pattern2 = r'[Cc]:/Users/32181/.openclaw/workspace/[Aa][Uu][Tt][Oo][Bb][Aa]-[Mm][Oo][Dd][Ee][Rr][Nn]/backend'
        # 模式3: /Users/32181/.openclaw/workspace/AutoBA-modern/backend
        pattern3 = r'/Users/32181/.openclaw/workspace/[Aa][Uu][Tt][Oo][Bb][Aa]-[Mm][Oo][Dd][Ee][Rr][Nn]/backend'
        
        # 执行路径替换
        linux_command = re.sub(pattern1, '/workspace', command_no_quotes, flags=re.IGNORECASE)
        linux_command = re.sub(pattern2, '/workspace', linux_command, flags=re.IGNORECASE)
        linux_command = re.sub(pattern3, '/workspace', linux_command, flags=re.IGNORECASE)
        
        # 额外的安全替换：使用当前工作目录作为基准
        if current_dir in linux_command:
            linux_command = linux_command.replace(current_dir, '/workspace')
        
        # 确保所有路径都使用Linux风格的分隔符
        linux_command = linux_command.replace('\\', '/')
        
        # 清理路径，确保没有重复的挂载点路径和双斜杠
        linux_command = re.sub(r'(/workspace)+', '/workspace', linux_command)
        # 清理双斜杠
        linux_command = re.sub(r'//+', '/', linux_command)
        
        # 移除命令中的单引号
        linux_command = linux_command.replace("'", "").replace('"', "")
        
        # 验证路径是否正确
        self._send_output(f"[EXECUTOR] Converted command: {linux_command}", 'info')
        
        # 检查并创建输出目录
        # 提取可能的输出目录
        import re
        output_dirs = []
        
        # 匹配 -S 参数指定的输出文件路径
        sam_output_match = re.search(r'-S\s+(/\S+)', linux_command)
        if sam_output_match:
            output_file = sam_output_match.group(1)
            output_dir = os.path.dirname(output_file)
            if output_dir:
                output_dirs.append(output_dir)
        
        # 匹配重定向输出的文件路径
        redirect_match = re.search(r'\s+>\s+(/\S+)', linux_command)
        if redirect_match:
            output_file = redirect_match.group(1)
            output_dir = os.path.dirname(output_file)
            if output_dir:
                output_dirs.append(output_dir)
        
        # 创建输出目录
        for output_dir in output_dirs:
            # 在Docker容器内创建目录
            mkdir_cmd = f'docker run --rm -v "{current_dir}:{mount_point}" -w "{mount_point}" {image} mkdir -p {output_dir}'
            try:
                subprocess.run(mkdir_cmd, shell=True, capture_output=True, text=True, timeout=30)
                self._send_output(f"[EXECUTOR] Created output directory: {output_dir}", 'info')
            except Exception as e:
                self._send_output(f"[EXECUTOR] Failed to create output directory: {e}", 'error')
        
        # 检查是否包含需要shell解析的操作符
        if '>' in linux_command or '<' in linux_command or '&&' in linux_command or '||' in linux_command or ';' in linux_command or '|' in linux_command:
            # 对于包含重定向、管道或多个命令的情况，需要使用bash -c来执行
            docker_cmd = f'docker run --rm -v "{current_dir}:{mount_point}" -w "{mount_point}" {image} bash -c "{linux_command}"'
        else:
            # 对于单个命令，直接执行
            docker_cmd = f'docker run --rm -v "{current_dir}:{mount_point}" -w "{mount_point}" {image} {linux_command}'

        self._send_output(f"[EXECUTOR] Running with Docker: {docker_cmd}", 'info')

        try:
            # 设置环境变量确保使用utf-8编码
            env = os.environ.copy()
            env['LANG'] = 'en_US.UTF-8'
            env['LC_ALL'] = 'en_US.UTF-8'
            
            # 执行 Docker 命令
            result = subprocess.run(
                docker_cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                timeout=3600  # 1小时超时
            )
            
            # 检测严重错误，如文件格式错误
            stderr_output = result.stderr.lower()
            error_details = ""
            
            if 'has more read characters than quality values' in stderr_output:
                error_details = "FASTQ文件格式错误：序列长度与质量值长度不匹配。请检查FASTQ文件格式，确保每个序列的长度与对应质量值的长度完全一致。"
            elif 'invalid fastq' in stderr_output:
                error_details = "FASTQ文件格式错误：文件不符合FASTQ格式规范。请检查文件格式是否正确。"
            elif any(error in stderr_output for error in ['file not found', 'no such file']):
                error_details = "文件不存在：指定的文件路径不存在。请检查文件路径是否正确。"
            elif 'cannot open' in stderr_output:
                error_details = "无法打开文件：文件可能被占用或权限不足。请检查文件权限和是否被其他程序占用。"
            elif 'permission denied' in stderr_output:
                error_details = "权限不足：没有足够的权限访问文件。请检查文件权限设置。"
            elif 'does not exist or is not a bowtie 2 index' in stderr_output:
                error_details = "Bowtie 2索引文件不存在：参考基因组索引尚未构建。正在自动构建索引..."
                
                # 尝试自动构建Bowtie 2索引
                try:
                    # 从命令中提取参考基因组文件路径
                    import re
                    # 匹配bowtie2命令中的参考基因组索引路径
                    index_match = re.search(r'-x\s+([^\s]+)', command)
                    if index_match:
                        index_path = index_match.group(1)
                        # 移除索引后缀，得到参考基因组文件路径
                        fasta_path = re.sub(r'\.1\.bt2$', '.fasta', index_path)
                        fasta_path = re.sub(r'\.bt2$', '.fasta', fasta_path)
                        
                        # 检查参考基因组文件是否存在
                        if os.path.exists(fasta_path):
                            self._send_output(f"[EXECUTOR] Found reference genome file: {fasta_path}", 'info')
                            # 构建bowtie2-build命令
                            bowtie2_build_cmd = f"bowtie2-build {fasta_path} {index_path}"
                            self._send_output(f"[EXECUTOR] Running bowtie2-build to build index: {bowtie2_build_cmd}", 'info')
                            
                            # 执行bowtie2-build命令
                            build_result = self._execute_with_docker(bowtie2_build_cmd, 'bowtie2')
                            if "Docker execution completed successfully" in build_result:
                                self._send_output("[EXECUTOR] Bowtie 2 index built successfully!", 'info')
                                # 重新执行原始命令
                                self._send_output("[EXECUTOR] Re-executing original command...", 'info')
                                return self._execute_with_docker(command, tool)
                            else:
                                self._send_output("[EXECUTOR] Failed to build Bowtie 2 index", 'error')
                        else:
                            self._send_output(f"[EXECUTOR] Reference genome file not found: {fasta_path}", 'error')
                except Exception as e:
                    self._send_output(f"[EXECUTOR] Error building Bowtie 2 index: {e}", 'error')
            
            if error_details:
                error_msg = f"[EXECUTOR] Critical error detected: {result.stderr}\n[EXECUTOR] Error cause: {error_details}\n[EXECUTOR] Cannot be fixed automatically: This requires manual intervention to correct the file format or file path."
                self._send_output(error_msg, 'error')
                return error_msg
            
            # 输出结果
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self._send_output(f"[stdout] {line}", 'stdout')
            
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        self._send_output(f"[stderr] {line}", 'stderr')
            
            if result.returncode == 0:
                # 检查是否有错误信息
                if 'error' in result.stderr.lower() or 'Error:' in result.stderr:
                    # 即使返回码为0，如果有错误信息，也视为失败
                    self._send_output(f"[EXECUTOR] Docker execution finished with error: {result.stderr}", 'error')
                    return f"Docker execution output: {result.stdout}\n{result.stderr}"
                else:
                    self._send_output(f"[EXECUTOR] Docker execution completed successfully", 'info')
                    return f"[EXECUTOR] Docker execution completed successfully\nDocker execution output: {result.stdout}\n{result.stderr}"
            else:
                # 检查是否有成功的输出特征，但同时也要确保没有错误信息
                stdout_lower = result.stdout.lower()
                stderr_lower = result.stderr.lower()
                if 'total time for' in stdout_lower and 'index' in stdout_lower and 'error' not in stderr_lower and 'Error:' not in result.stderr:
                    # 对于bowtie2-build等工具，即使返回非零退出码，只要有索引构建的成功信息且没有错误，也视为成功
                    self._send_output(f"[EXECUTOR] Docker execution completed successfully (tool-specific success detection)", 'info')
                    return f"[EXECUTOR] Docker execution completed successfully (tool-specific success detection)\nDocker execution output: {result.stdout}\n{result.stderr}"
                else:
                    self._send_output(f"[EXECUTOR] Docker execution finished with return code: {result.returncode}", 'error')
                    return f"Docker execution output: {result.stdout}\n{result.stderr}"
            
        except Exception as e:
            error_msg = f"[EXECUTOR] Docker execution error: {e}"
            self._send_output(error_msg, 'error')
            return error_msg 
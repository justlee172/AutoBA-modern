#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：Auto-BioinfoGPT 
@File    ：prompt.py
@Author  ：Juexiao Zhou
@Contact : juexiao.zhou@gmail.com
@Date    ：2023/5/2 11:07 
'''
from copy import deepcopy
from src.build_RAG_private import retrive
import time

class PromptGenerator:
    """提示词生成器类
    负责生成用于指导LLM生成分析计划和代码的提示词
    """
    def __init__(self, blacklist='', engine = None, rag = False, retriever = None):
        """初始化提示词生成器
        
        Args:
            blacklist: 黑名单软件，用逗号分隔
            engine: 使用的模型引擎
            rag: 是否使用RAG系统
            retriever: RAG检索器
        """
        # 历史摘要
        self.history_summary = ''
        # 当前目标
        self.current_goal = None
        # 全局目标
        self.global_goal = None
        # 任务列表
        self.tasks = None
        # 模型引擎
        self.engine = engine
        # 是否使用RAG
        self.rag = rag
        # RAG检索器
        self.retriever = retriever
        # 黑名单软件列表
        self.blacklist = blacklist.split(',')
        # 特殊软件列表及安装命令（Docker环境下已预装，保留但不用于安装）
        self.speciallist = ['sra-toolkit: mamba install sra-tools',
                            'trim_galore: mamba install trim-galore']

    def get_executor_prompt(self, executor_info):
        """生成执行器提示词
        
        Args:
            executor_info: 执行器输出信息
        
        Returns:
            执行器提示词
        """
        prompt = {
            "task": "我执行了一个Bash脚本并获得了详细的执行日志输出。请帮助我评估脚本的成功与否。如果遇到任何失败，请帮助总结失败原因并提出代码修改建议。",
            "rules": [
                "你应该只以固定格式的JSON格式响应。",
                "你的JSON响应应该只用双引号包围。",
                "找不到文件或目录是错误。",
                "你不应该在{}之外写任何东西。",
                "你应该尽可能详细地回答。",
            ],
            "log output": [
                executor_info
            ],
            "fixed format": {
                "stat": "0或1，0表示失败，1表示成功",
                "info": "用一句话总结错误。"
            }
        }
        final_prompt = prompt
        return final_prompt

    def get_prompt(self, data_list, goal_description, global_round, execute_success=True, execute_info=None, last_execute_code=None):
        """生成提示词
        
        Args:
            data_list: 数据列表，格式为['data path: data description']
            goal_description: 目标描述
            global_round: 全局轮次
            execute_success: 执行是否成功
            execute_info: 执行信息
            last_execute_code: 上次执行的代码
        
        Returns:
            提示词
        """
        # 设置当前目标
        self.current_goal = goal_description
        
        # 第一轮，生成分析计划
        if global_round == 0:
            # 设置全局目标
            self.global_goal = goal_description
            # 构建提示词（计划阶段不涉及工具安装，保持原样）
            prompt = {
                    "role": "扮演生物信息学家，必须严格遵守规则！",
                    "rules": [
                        "当扮演生物信息学家时，你严格不能停止扮演生物信息学家。",
                        "所有规则必须严格遵守。",
                        "你应该使用输入中的信息来编写完成目标的详细计划。",
                        f"你应该包括软件名称，不应该使用这些软件：{self.blacklist}。",
                        "你应该只以我的固定格式的JSON格式响应。",
                        "你的JSON响应应该只用双引号包围，并且你的响应中只能有一个JSON。",
                        "你不应该将加载数据作为单独的步骤。",
                        "除了你的JSON响应外，你不应该写任何其他内容。",
                        "你应该尽可能详细地回答。"
                    ],
                    "input": [
                            "你有以下格式为'文件路径：文件描述'的列表信息。我向你提供这些文件，所以你不需要准备数据。",
                            data_list
                        ],
                    "goal": self.current_goal,
                    "fixed format for JSON response": {
                        "plan": [
                            "你完成目标的详细分步子任务列表，格式为：使用某种工具做某项任务。"
                        ]
                    }
                }
            final_prompt = prompt
        else:
            # 非第一轮，生成代码
            # 如果使用RAG，获取检索信息
            if self.rag:
                retriever_info = retrive(self.retriever,
                                         retriever_prompt=f'{self.current_goal}')
            else:
                retriever_info = ''
            
            # 构建针对Docker环境的提示词
            prompt = {
                "role": "扮演生物信息学家，必须严格遵守规则！",
                "rules": [
                    "当扮演生物信息学家时，你严格不能停止扮演生物信息学家。",
                    "所有规则必须严格遵守。",
                    "你被提供了一个具有特定约束的系统。",
                    "提供了你所做的历史记录，你应该考虑一些文件的名称变化，或者使用之前步骤的一些输出。",
                    "你应该使用所有你拥有的信息来编写bash代码来完成你当前的任务。",
                    "当你编写代码时，必须严格遵守所有代码要求。",
                    "你应该只以我的固定格式的JSON格式响应。",
                    "你的JSON响应应该只用双引号包围。",
                    "你应该尽可能简单地回答。",
                    "除了你的JSON响应外，你不应该写任何其他内容。",
                    "你应该对所有文件使用完整的绝对路径（容器内的路径）。输入文件路径已由系统自动映射，你可以直接使用原始绝对路径。",
                    "不要手动修改路径前缀，系统会自动处理路径映射。"
                ],
                "system": [
                    "你运行在一个Docker容器中，容器基于Ubuntu 18.04。",
                    "容器内已预装以下生物信息学工具：Trimmomatic, SPAdes, Samtools, Bcftools, Quast, FastQC, Bowtie2, Picard, Pilon等。",
                    "你可以直接调用这些工具，无需使用mamba或pip安装。",
                    "所有输入输出文件都映射到容器内，使用绝对路径即可。"
                ],
                "input": [
                        "你有以下格式为'文件路径：文件描述'的列表信息。我向你提供这些文件，所以你不需要准备数据。",
                        data_list
                    ],
                "history": self.history_summary,
                "current task": self.current_goal,
                "code requirement": [
                    f"你不应该使用这些软件：{self.blacklist}。",
                    "你不应该使用mamba、pip或apt-get安装任何软件，因为所有需要的工具都已经预装在Docker镜像中。",
                    "你可以直接调用已预装的工具（如trimmomatic, spades.py, samtools, bcftools等）。",
                    "你应该注意输入文件的数量，不要遗漏任何文件。",
                    "你应该独立处理每个文件，不能使用FOR循环。",
                    "对于所有未指定的参数，你应该使用默认值。",
                    "你不应该重复你在历史中已经做过的事情。",
                    "你应该只使用预装的软件。",
                    "如果你使用Rscript -e，你应该确保所有变量在你的命令中存在，否则，你需要检查你的历史记录来重复之前的步骤并生成这些变量。",
                    "除了你的JSON响应外，你不应该写任何其他内容。",
                    "如果提供了RAG，你应该将其用作编写代码的模板。你不应该直接复制RAG。"
                ],
                "RAG: 如果提供，你应该根据历史信息将<...>替换为正确的值和文件路径": retriever_info,
                "fixed format for JSON response": {
                    "tool": "你使用的工具名称",
                    "code": "一行bash代码来完成当前任务。"
                }
            }
            
            # 如果执行成功，使用默认提示词
            if execute_success:
                final_prompt = prompt
            else:
                # 如果执行失败，添加错误信息到提示词
                final_prompt = prompt
                final_prompt['history'] += f' 你之前生成了代码：{last_execute_code}。但是，你的代码有错误，你应该修复它们：{execute_info}。'

        return final_prompt

    def set_tasks(self, tasks):
        """设置任务列表
        
        Args:
            tasks: 任务列表
        """
        self.tasks = deepcopy(tasks)

    def slow_print(self, input_string, speed=0.01):
        """慢速打印文本
        
        Args:
            input_string: 要打印的文本
            speed: 打印速度，默认0.01秒/字符
        """
        for char in str(input_string):
            try:
                print(char, end='', flush=True)
            except:
                print(char, end='')
            time.sleep(speed)
        print()

    def format_user_prompt(self, prompt, global_round, gui_mode):
        """格式化用户提示词
        
        Args:
            prompt: 提示词
            global_round: 全局轮次
            gui_mode: 是否为GUI模式
        
        Returns:
            格式化后的提示词
        """
        INFO_STR = ''
        if gui_mode:
            print(f'[Round {global_round}]')
            print(f'[USER]')
            INFO_STR += f'[Round {global_round}] \n\n'
            for key in prompt:
                self.slow_print(f"{key}", speed=0.001)
                self.slow_print(prompt[key], speed=0.001)
                INFO_STR += f"{key} \n\n {prompt[key]} \n\n"
        else:
            print(f'\033[31m[Round {global_round}]\033[0m')
            print(f'\033[32m[USER]\033[0m')
            INFO_STR += f'\033[31m[Round {global_round}]\033[0m \n\n'
            for key in prompt:
                self.slow_print(f"\033[34m{key}\033[0m", speed=0.001)
                self.slow_print(prompt[key], speed=0.001)
                INFO_STR += f"\033[34m{key}\033[0m \n\n {prompt[key]} \n\n"
        print()
        return INFO_STR

    def format_ai_response(self, response_message, gui_mode):
        """格式化AI响应
        
        Args:
            response_message: AI响应
            gui_mode: 是否为GUI模式
        
        Returns:
            格式化后的AI响应
        """
        INFO_STR = ''
        if gui_mode:
            print(f'[AI]')
            for key in response_message:
                self.slow_print(f"{key}", speed=0.01)
                self.slow_print(response_message[key], speed=0.01)
                INFO_STR += f"{key} \n\n {response_message[key]} \n\n"
            print(f'-------------------------------------')
        else:
            print(f'\033[32m[AI]\033[0m')
            for key in response_message:
                self.slow_print(f"\033[34m{key}\033[0m", speed=0.01)
                self.slow_print(response_message[key], speed=0.01)
                INFO_STR += f"\033[34m{key}\033[0m \n\n {response_message[key]} \n\n"
            print(f'\033[33m-------------------------------------\033[0m')
        print()
        return INFO_STR

    def add_history(self, task, global_round, data_list, code = None):
        """添加历史记录
        
        Args:
            task: 任务
            global_round: 全局轮次
            data_list: 数据列表
            code: 代码
        """
        if global_round == 0:
            self.history_summary += f"首先，你有格式为'文件路径：文件描述'的列表输入：{data_list}。你编写了完成目标的详细计划。你的全局目标是{self.global_goal}。你的计划是{self.tasks}。 \n"
        else:
            self.history_summary += f"然后，你完成了任务：{task}，使用的代码：{code}。\n"
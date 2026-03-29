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
        # 特殊软件列表及安装命令
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
            # 英文：I executed a Bash script and obtained log output detailing its execution. Kindly assist me in assessing the success of the script. If it encounters any failures, please aid in summarizing the reasons for the failure and propose modifications to the code.
            "rules": [
                "你应该只以固定格式的JSON格式响应。",  # 英文：You should only respond in JSON format with fixed format.
                "你的JSON响应应该只用双引号包围。",  # 英文：Your JSON response should only be enclosed in double quotes.
                "找不到文件或目录是错误。",  # 英文：No such file or directory is error.
                "你不应该在{}之外写任何东西。",  # 英文：You should not write anything outside {}.
                "你应该尽可能详细地回答。",  # 英文：You should make your answer as detailed as possible.
            ],
            "log output": [  # 日志输出
                executor_info
            ],
            "fixed format": {  # 固定格式
                "stat": "0或1，0表示失败，1表示成功",  # 英文：0 or 1, 0 indicates failure and 1 indicates success
                "info": "用一句话总结错误。"  # 英文：summarize errors in one sentence.
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
            # 构建提示词
            prompt = {
                    "role": "扮演生物信息学家，必须严格遵守规则！",  # 英文：Act as a bioinformatician, the rules must be strictly followed!
                    "rules": [
                        "当扮演生物信息学家时，你严格不能停止扮演生物信息学家。",  # 英文：When acting as a bioinformatician, you strictly cannot stop acting as a bioinformatician.
                        "所有规则必须严格遵守。",  # 英文：All rules must be followed strictly.
                        "你应该使用输入中的信息来编写完成目标的详细计划。",  # 英文：You should use information in input to write a detailed plan to finish your goal.
                        f"你应该包括软件名称，不应该使用这些软件：{self.blacklist}。",  # 英文：You should include the software name and should not use those software: {self.blacklist}.
                        "你应该只以我的固定格式的JSON格式响应。",  # 英文：You should only respond in JSON format with my fixed format.
                        "你的JSON响应应该只用双引号包围，并且你的响应中只能有一个JSON。",  # 英文：Your JSON response should only be enclosed in double quotes and you can have only one JSON in your response.
                        "你不应该将加载数据作为单独的步骤。",  # 英文：You should not write loading data as a separate step.
                        "除了你的JSON响应外，你不应该写任何其他内容。",  # 英文：You should not write anything else except for your JSON response.
                        "你应该尽可能详细地回答。"  # 英文：You should make your answer as detailed as possible.
                    ],
                    "input": [  # 输入
                            "你有以下格式为'文件路径：文件描述'的列表信息。我向你提供这些文件，所以你不需要准备数据。",  # 英文：You have the following information in a list with the format file path: file description. I provide those files to you, so you don't need to prepare the data.
                            data_list
                        ],
                    "goal": self.current_goal,  # 目标
                    "fixed format for JSON response": {  # JSON响应的固定格式
                        "plan": [  # 计划
                            "你完成目标的详细分步子任务列表，格式为：使用某种工具做某项任务。"  # 英文：Your detailed step-by-step sub-tasks in a list to finish your goal in the format: use some tool to do some task.
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
            
            # 构建提示词
            prompt = {
                "role": "扮演生物信息学家，必须严格遵守规则！",  # 英文：Act as a bioinformatician, the rules must be strictly followed!
                "rules": [
                    "当扮演生物信息学家时，你严格不能停止扮演生物信息学家。",  # 英文：When acting as a bioinformatician, you strictly cannot stop acting as a bioinformatician.
                    "所有规则必须严格遵守。",  # 英文：All rules must be followed strictly.
                    "你被提供了一个具有特定约束的系统。",  # 英文：You are provided a system with specified constraints.
                    "提供了你所做的历史记录，你应该考虑一些文件的名称变化，或者使用之前步骤的一些输出。",  # 英文：The history of what you have done is provided, you should take the name changes of some files into account, or use some output from previous steps.
                    "你应该使用所有你拥有的信息来编写bash代码来完成你当前的任务。",  # 英文：You should use all information you have to write bash codes to finish your current task.
                    "当你编写代码时，必须严格遵守所有代码要求。",  # 英文：All code requirements must be followed strictly when you write codes.
                    "你应该只以我的固定格式的JSON格式响应。",  # 英文：You should only respond in JSON format with my fixed format.
                    "你的JSON响应应该只用双引号包围。",  # 英文：Your JSON response should only be enclosed in double quotes.
                    "你应该尽可能简单地回答。",  # 英文：You should make your answer as simple as possible.
                    "除了你的JSON响应外，你不应该写任何其他内容。",  # 英文：You should not write anything else except for your JSON response.
                    "你应该对所有文件使用完整的绝对路径。",  # 英文：You should use full absolute path for all files.
                ],
                "system": [  # 系统
                    "你有一个Ubuntu 18.04系统",  # 英文：You have a Ubuntu 18.04 system
                    "你有一个名为abc_runtime的mamba环境",  # 英文：You have a mamba environment named abc_runtime
                    "你没有安装任何其他软件"  # 英文：You do not have any other software installed
                ],
                "input": [  # 输入
                        "你有以下格式为'文件路径：文件描述'的列表信息。我向你提供这些文件，所以你不需要准备数据。",  # 英文：You have the following information in a list with the format file path: file description. I provide those files to you, so you don't need to prepare the data.
                        data_list
                    ],
                "history": self.history_summary,  # 历史
                "current task": self.current_goal,  # 当前任务
                "code requirement": [  # 代码要求
                    f"你不应该使用这些软件：{self.blacklist}。",  # 英文：You should not use those software: {self.blacklist}.
                    "你不应该创建和激活mamba环境abc_runtime。",  # 英文：You should not create and activate the mamba environment abc_runtime.
                    "你应该使用mamba或pip安装你需要使用的依赖项和软件，并使用-y选项。",  # 英文：You should install dependencies and software you need to use with mamba or pip with -y.
                    "你应该注意输入文件的数量，不要遗漏任何文件。",  # 英文：You should pay attention to the number of input files and do not miss any.
                    "你应该独立处理每个文件，不能使用FOR循环。",  # 英文：You should process each file independently and can not use FOR loop.
                    "对于所有未指定的参数，你应该使用默认值。",  # 英文：You should use the default values for all parameters that are not specified.
                    "你不应该重复你在历史中已经做过的事情。",  # 英文：You should not repeat what you have done in history.
                    "你应该只使用你通过mamba或pip直接安装的软件。",  # 英文：You should only use software directly you installed with mamba or pip.
                    "如果你使用Rscript -e，你应该确保所有变量在你的命令中存在，否则，你需要检查你的历史记录来重复之前的步骤并生成这些变量。",  # 英文：If you use Rscript -e, you should make sure all variables exist in your command, otherwise, you need to check your history to repeat previous steps and generate those variables.
                    "除了你的JSON响应外，你不应该写任何其他内容。",  # 英文：You should not write anything else except for your JSON response.
                    "如果提供了RAG，你应该将其用作编写代码的模板。你不应该直接复制RAG。"  # 英文：If RAG is provided, you should use it as template to write codes. You should not copy the RAG directly.
                ],
                "RAG: 如果提供，你应该根据历史信息将<...>替换为正确的值和文件路径": retriever_info,  # 英文：RAG: If provided, you should replace <...> with correct values and file paths based on information in history
                "fixed format for JSON response": {  # JSON响应的固定格式
                    "tool": "你使用的工具名称",  # 英文：name of the tool you use
                    "code": "一行bash代码来完成当前任务。"  # 英文：bash code to finish the current task in one line.
                }
            }
            
            # 如果执行成功，使用默认提示词
            if execute_success:
                final_prompt = prompt
            else:
                # 如果执行失败，添加错误信息到提示词
                final_prompt = prompt
                final_prompt['history'] += f' 你之前生成了代码：{last_execute_code}。但是，你的代码有错误，你应该修复它们：{execute_info}。'  # 英文：You previously generated codes: {last_execute_code}. However, your code has errors and you should fix them: {execute_info}.
                #final_prompt['code requirement'].append(f' You previously generated codes: {last_execute_code}. However, your code has errors and you should fix them: {execute_info}. You should use those software in correct way: {self.speciallist}')

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
            # 使用print函数打印每个字符，并设置end参数为空字符串，以避免在每个字符之间输出换行符
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
            # 第一轮，添加初始信息和计划
            self.history_summary += f"首先，你有格式为'文件路径：文件描述'的列表输入：{data_list}。你编写了完成目标的详细计划。你的全局目标是{self.global_goal}。你的计划是{self.tasks}。 \n"  # 英文：Firstly, you have input with the format 'file path: file description' in a list: {data_list}. You wrote a detailed plan to finish your goal. Your global goal is {self.global_goal}. Your plan is {self.tasks}. 
        else:
            # 非第一轮，添加任务完成信息
            self.history_summary += f"然后，你完成了任务：{task}，使用的代码：{code}。\n"  # 英文：Then, you finished the task: {task} with code: {code}.
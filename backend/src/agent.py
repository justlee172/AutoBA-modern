#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
AutoBA Agent - 支持 Kimi/Lobster API
'''

import os
import os.path
import threading
import time
import json
import sys

try:
    import torch.cuda
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from src.prompt import PromptGenerator
from src.spinner import Spinner
from src.executor import CodeExecutor
import httpx

class Agent:
    def __init__(self, initial_data_list, output_dir, initial_goal_description, model_engine,
                 openai_api, execute=True, blacklist='', gui_mode=False, cpu=False, rag=False):
        
        self.initial_data_list = initial_data_list
        self.initial_goal_description = initial_goal_description
        self.tasks = []
        self.update_data_lists = [_ for _ in initial_data_list]
        self.output_dir = output_dir
        self.update_data_lists.append(f'{output_dir}: all outputs should be stored under this dir')
        
        self.model_engine = model_engine
        self.openai_api = openai_api
        self.rag = rag
        self.blacklist = blacklist
        
        # 支持的模型
        self.valid_model_engines = ['gpt-4o', 'gpt-4o-mini', 'gpt-4', 'gpt-3.5-turbo', 'kimi', 'lobster']
        
        self.generator = PromptGenerator(blacklist=blacklist, engine=model_engine, rag=rag, retriever=None)
        self.global_round = 0
        self.execute = execute
        self.execute_success = True
        self.execute_info = ''
        self.code_executor = CodeExecutor()
        self.gui_mode = gui_mode
        self.cpu = cpu
        self.paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        
        # 分步执行相关
        self.steps = []
        self.current_step = 0
        self.step_status = []
        
        if model_engine not in self.valid_model_engines:
            print(f'[ERROR] Invalid model: {model_engine}')
            exit()
        
        print(f'[INFO] Using model: {model_engine}')

    def get_single_response(self, prompt):
        """调用 Kimi API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api}"
        }
        
        # Kimi 模型名
        model_name = "moonshot-v1-8k"
        
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": str(prompt)}],
            "max_tokens": 4096,
            "temperature": 0
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"[INFO] API request attempt {retry_count + 1}/{max_retries}")
                response = httpx.post(
                    "https://api.moonshot.cn/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=180.0,
                    verify=False
                )
                response.raise_for_status()
                response_data = response.json()
                print(f"[INFO] API request successful")
                return response_data["choices"][0]["message"]["content"]
            except Exception as e:
                retry_count += 1
                print(f"[API Error] Attempt {retry_count}: {e}")
                if retry_count < max_retries:
                    wait_time = retry_count * 5
                    print(f"[INFO] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"[API Error] Max retries reached")
                    raise

    def valid_json_response(self, response_message):
        if not os.path.isdir(f'{self.output_dir}'):
            os.makedirs(f'{self.output_dir}')
        try:
            # 替换中文引号为英文引号
            response_message = response_message.replace('“', '"').replace('”', '"')
            with open(f'{self.output_dir}/{self.global_round}_response.json', 'w') as w:
                json.dump(json.loads(response_message), w)
            json.load(open(f'{self.output_dir}/{self.global_round}_response.json'))
        except Exception as e:
            print('[INVALID RESPONSE]\n', response_message)
            print(f'[ERROR] {e}')
            return False
        return True

    def valid_json_response_executor(self, response_message):
        if not os.path.isdir(f'{self.output_dir}'):
            os.makedirs(f'{self.output_dir}')
        try:
            # 替换中文引号为英文引号
            response_message = response_message.replace('“', '"').replace('”', '"')
            with open(f'{self.output_dir}/executor_response.json', 'w') as w:
                json.dump(json.loads(response_message), w)
            tmp_data = json.load(open(f'{self.output_dir}/executor_response.json'))
            if str(tmp_data.get('stat', '')) not in ['0', '1']:
                return False
        except Exception as e:
            print('[INVALID RESPONSE]\n', response_message)
            print(f'[ERROR] {e}')
            return False
        return True

    def find_json(self, response_message):
        if "```json\n" in response_message:
            start = response_message.find("{")
            end = response_message.rfind("}") + 1
            return response_message[start:end]
        elif "```bash\n" in response_message:
            start = response_message.find("```bash\n")
            end = response_message.find("```\n")
            return str({'tool':'', 'code': response_message[start:end].lstrip('```bash\n')})
        else:
            start = response_message.find("{")
            end = response_message.rfind("}") + 1
            return response_message[start:end]

    def execute_code(self, response_message):
        if not os.path.isdir(f'{self.output_dir}'):
            os.makedirs(f'{self.output_dir}')
        try:
            with open(f'{self.output_dir}/{self.global_round}.sh', 'w') as w:
                w.write(response_message.get('code', ''))
            
            if self.execute:
                self.last_execute_code = response_message.get('code', '')
                executor_info = self.code_executor.execute(bash_code_path=f'{self.output_dir}/{self.global_round}.sh')
                
                if len(executor_info) == 0:
                    return True, 'No error'
                
                executor_response = self.get_single_response(self.generator.get_executor_prompt(executor_info=executor_info))
                
                if 'llama' in self.model_engine or 'deepseek' in self.model_engine:
                    executor_response = self.find_json(executor_response)
                
                max_tries = 3
                n_tries = 0
                while not self.valid_json_response_executor(executor_response) and n_tries < max_tries:
                    executor_response = self.get_single_response(self.generator.get_executor_prompt(executor_info=executor_info))
                    n_tries += 1
                
                executor_response = json.load(open(f'{self.output_dir}/executor_response.json'))
                return bool(int(executor_response.get('stat', 0))), executor_response.get('info', '')
            
            return True, 'Skipped execution'
        except Exception as e:
            return False, str(e)

    def run_plan_phase(self):
        self.pause_event.wait()
        init_prompt = self.generator.get_prompt(
            data_list=self.initial_data_list,
            goal_description=self.initial_goal_description,
            global_round=self.global_round,
            execute_success=self.execute_success,
            execute_info=self.execute_info
        )
        
        with Spinner('[AI Thinking...]'):
            self.pause_event.wait()
            response_message = self.get_single_response(init_prompt)
            if 'llama' in self.model_engine or 'deepseek' in self.model_engine:
                response_message = self.find_json(response_message)
            
            while not self.valid_json_response(response_message):
                self.pause_event.wait()
                print('[Invalid Response, Retrying...]')
                response_message = self.get_single_response(init_prompt)
            
            response_message = json.load(open(f'{self.output_dir}/{self.global_round}_response.json'))
        
        self.tasks = response_message.get('plan', [])
        self.generator.set_tasks(self.tasks)
        
        # 初始化步骤列表
        self.steps = []
        self.step_status = []
        for i, task in enumerate(self.tasks):
            self.steps.append({
                'id': i + 1,
                'description': task,
                'status': 'pending',
                'start_time': None,
                'end_time': None,
                'execution_info': ''
            })
            self.step_status.append('pending')
        
        self.generator.add_history(None, self.global_round, self.update_data_lists)
        self.global_round += 1

    def run_code_generation_phase(self):
        import time
        
        while len(self.tasks) > 0:
            self.pause_event.wait()
            task = self.tasks.pop(0)
            step_index = self.current_step
            
            # 更新步骤状态为运行中
            if step_index < len(self.steps):
                self.steps[step_index]['status'] = 'running'
                self.steps[step_index]['start_time'] = time.time()
                self.step_status[step_index] = 'running'
                print(f'[STEP {step_index + 1}/{len(self.steps)}] 开始执行: {task}')
            
            prompt = self.generator.get_prompt(
                data_list=self.update_data_lists,
                goal_description=task,
                global_round=self.global_round,
                execute_success=self.execute_success,
                execute_info=self.execute_info
            )
            
            self.first_prompt = True
            self.execute_success = False
            max_retries = 3
            retry_count = 0
            
            while not self.execute_success and retry_count < max_retries:
                self.pause_event.wait()
                
                if not self.first_prompt:
                    prompt = self.generator.get_prompt(
                        data_list=self.update_data_lists,
                        goal_description=task,
                        global_round=self.global_round,
                        execute_success=self.execute_success,
                        execute_info=self.execute_info,
                        last_execute_code=self.last_execute_code
                    )
                
                with Spinner('[AI Thinking...]'):
                    response_message = self.get_single_response(prompt)
                    if 'llama' in self.model_engine or 'deepseek' in self.model_engine:
                        response_message = self.find_json(response_message)
                    
                    json_retries = 0
                    max_json_retries = 3
                    while not self.valid_json_response(response_message) and json_retries < max_json_retries:
                        print('[Invalid Response, Retrying...]')
                        response_message = self.get_single_response(prompt)
                        json_retries += 1
                    
                    if json_retries >= max_json_retries:
                        print('[ERROR] Max JSON parsing retries reached')
                        # 更新步骤状态为失败
                        if step_index < len(self.steps):
                            self.steps[step_index]['status'] = 'failed'
                            self.steps[step_index]['end_time'] = time.time()
                            self.steps[step_index]['execution_info'] = 'JSON解析失败，达到最大重试次数'
                            self.step_status[step_index] = 'failed'
                        return False
                    
                    response_message = json.load(open(f'{self.output_dir}/{self.global_round}_response.json'))
                
                with Spinner('[AI Executing...]'):
                    execute_success, execute_info = self.execute_code(response_message)
                    self.execute_success = execute_success
                    self.execute_info = execute_info
                
                if not self.execute_success:
                    # 检查是否是严重错误
                    if any(error in execute_info.lower() for error in [
                        'critical error',
                        'has more read characters than quality values',
                        'invalid fastq',
                        'file not found',
                        'no such file',
                        'cannot open',
                        'permission denied',
                        'does not exist or is not a bowtie 2 index',
                        'script only contains mamba install commands'
                    ]):
                        print(f'[CRITICAL ERROR] {execute_info}')
                        print('[INFO] Stopping execution due to critical error')
                        # 更新步骤状态为失败
                        if step_index < len(self.steps):
                            self.steps[step_index]['status'] = 'failed'
                            self.steps[step_index]['end_time'] = time.time()
                            self.steps[step_index]['execution_info'] = f'严重错误: {execute_info}'
                            self.step_status[step_index] = 'failed'
                        return False
                    self.first_prompt = False
                    retry_count += 1
                    print(f'[INFO] Retry {retry_count}/{max_retries} for task')
            
            if retry_count >= max_retries:
                print('[ERROR] Max execution retries reached')
                # 更新步骤状态为失败
                if step_index < len(self.steps):
                    self.steps[step_index]['status'] = 'failed'
                    self.steps[step_index]['end_time'] = time.time()
                    self.steps[step_index]['execution_info'] = '执行失败，达到最大重试次数'
                    self.step_status[step_index] = 'failed'
                return False
            
            # 更新步骤状态为完成
            if step_index < len(self.steps):
                self.steps[step_index]['status'] = 'completed'
                self.steps[step_index]['end_time'] = time.time()
                self.steps[step_index]['execution_info'] = execute_info
                self.step_status[step_index] = 'completed'
                print(f'[STEP {step_index + 1}/{len(self.steps)}] 执行完成: {task}')
            
            self.generator.add_history(task, self.global_round, self.update_data_lists, code=response_message.get('code', ''))
            self.global_round += 1
            self.current_step += 1
        return True

    def pause(self):
        """暂停执行"""
        if not self.paused:
            self.paused = True
            self.pause_event.clear()
            print('[INFO] Task paused')

    def resume(self):
        """继续执行"""
        if self.paused:
            self.paused = False
            self.pause_event.set()
            print('[INFO] Task resumed')
    
    def get_steps(self):
        """获取步骤状态信息"""
        return {
            'steps': self.steps,
            'current_step': self.current_step,
            'total_steps': len(self.steps),
            'step_status': self.step_status
        }

    def run(self):
        self.run_plan_phase()
        success = self.run_code_generation_phase()
        if success:
            print('[Job Finished!]')
        else:
            print('[Job Stopped Due to Critical Error!]')

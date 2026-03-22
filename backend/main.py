#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
AutoBA API Server - 支持真正的实时终端输出
使用简单的轮询机制 + Server-Sent Events
"""

import os
import sys
import asyncio
import uuid
import threading
import queue
import io
from datetime import datetime
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json

# AutoBA 路径
AUTUBA_PATH = os.path.dirname(os.path.abspath(__file__))  # backend 目录
sys.path.insert(0, AUTUBA_PATH)

# 全局变量
running_tasks = {}
task_queues = {}  # 每个任务一个队列用于实时推送
task_agents = {}  # 每个任务对应的agent实例

# FastAPI 应用
api = FastAPI(title="AutoBA API", version="2.1.0")

# CORS
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
try:
    FRONTEND_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if os.path.exists(FRONTEND_PATH):
        api.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")
except Exception as e:
    print(f"[Warning] Could not mount static files: {e}")
    FRONTEND_PATH = None


@api.get("/")
async def root():
    if FRONTEND_PATH:
        index_path = os.path.join(FRONTEND_PATH, "index.html")
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
    return {"message": "AutoBA API Server v2.1 - Real-time", "version": "2.1.0"}


@api.get("/health")
async def health_check():
    return {"status": "healthy"}


@api.get("/tasks")
async def list_tasks():
    return [
        {
            "task_id": tid,
            "goal": info.get("goal", ""),
            "status": info.get("status", "unknown"),
            "created_at": info.get("created_at", ""),
        }
        for tid, info in running_tasks.items()
    ]


@api.post("/task/create")
async def create_task(
    goal: str = Form(...),
    model_engine: str = Form("gpt-4o"),
    openai_api: str = Form(""),
    execute: bool = Form(True),
    file_descriptions: str = Form(""),
    files: List[UploadFile] = File(default=None),
):
    task_id = str(uuid.uuid4())
    
    task_dir = os.path.join(AUTUBA_PATH, "output", f"task_{task_id[:8]}")
    os.makedirs(task_dir, exist_ok=True)
    os.makedirs(os.path.join(task_dir, "data"), exist_ok=True)
    
    uploaded_files = []
    if files:
        for f in files:
            file_path = os.path.join(task_dir, "data", f.filename)
            with open(file_path, "wb") as pf:
                content = await f.read()
                pf.write(content)
            uploaded_files.append(f"{file_path}: uploaded file")
    
    task_info = {
        "task_id": task_id,
        "goal": goal,
        "model_engine": model_engine,
        "openai_api": openai_api,
        "execute": execute,
        "file_descriptions": file_descriptions,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "logs": [],
        "output_dir": task_dir,
        "uploaded_files": uploaded_files,
    }
    
    running_tasks[task_id] = task_info
    task_queues[task_id] = asyncio.Queue()
    
    asyncio.create_task(run_autoba_task(task_id, goal, model_engine, openai_api, execute, file_descriptions))
    
    return {"task_id": task_id, "status": "started"}


@api.get("/task/{task_id}")
async def get_task(task_id: str):
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return running_tasks[task_id]


@api.post("/task/{task_id}/pause")
async def pause_task(task_id: str):
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    if task_id in task_agents and hasattr(task_agents[task_id], 'pause'):
        task_agents[task_id].pause()
        running_tasks[task_id]["status"] = "paused"
        return {"status": "paused"}
    return {"status": "error", "message": "Agent not available"}

@api.post("/task/{task_id}/resume")
async def resume_task(task_id: str):
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    if task_id in task_agents and hasattr(task_agents[task_id], 'resume'):
        task_agents[task_id].resume()
        running_tasks[task_id]["status"] = "running"
        return {"status": "running"}
    return {"status": "error", "message": "Agent not available"}

@api.post("/task/{task_id}/stop")
async def stop_task(task_id: str):
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    running_tasks[task_id]["status"] = "stopped"
    # 清理agent实例
    if task_id in task_agents:
        del task_agents[task_id]
    return {"status": "stopped"}


@api.get("/task/{task_id}/steps")
async def get_task_steps(task_id: str):
    """获取任务的步骤状态信息"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_id in task_agents and hasattr(task_agents[task_id], 'get_steps'):
        steps_info = task_agents[task_id].get_steps()
        return {
            "task_id": task_id,
            "status": running_tasks[task_id].get("status", "unknown"),
            **steps_info
        }
    else:
        return {
            "task_id": task_id,
            "status": running_tasks[task_id].get("status", "unknown"),
            "steps": [],
            "current_step": 0,
            "total_steps": 0,
            "step_status": []
        }


@api.get("/task/{task_id}/logs")
async def get_task_logs(task_id: str):
    """获取任务日志 - 实时轮询接口"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    logs = running_tasks[task_id].get("logs", [])
    status = running_tasks[task_id].get("status", "unknown")
    
    return {
        "task_id": task_id,
        "status": status,
        "logs": logs
    }


@api.get("/task/{task_id}/stream")
async def stream_task_logs(task_id: str):
    """Server-Sent Events 流式日志"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    async def event_generator():
        last_index = 0
        
        while True:
            if task_id not in running_tasks:
                break
            
            status = running_tasks[task_id].get("status", "unknown")
            logs = running_tasks[task_id].get("logs", [])
            
            # 发送新日志
            while last_index < len(logs):
                log = logs[last_index]
                data = json.dumps({
                    "output": log.get("message", ""),
                    "type": log.get("type", "info"),
                    "timestamp": log.get("time", ""),
                    "status": status
                })
                yield f"data: {data}\n\n"
                last_index += 1
            
            # 如果任务完成，退出
            if status in ["completed", "failed", "stopped"]:
                break
            
            await asyncio.sleep(0.3)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@api.get("/task/{task_id}/files")
async def list_output_files(task_id: str):
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    output_dir = running_tasks[task_id].get("output_dir", "")
    if not output_dir or not os.path.exists(output_dir):
        return {"files": []}
    
    files = []
    for root, dirs, filenames in os.walk(output_dir):
        for f in filenames:
            if f.startswith('.'):
                continue
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, output_dir)
            files.append({
                "name": rel_path,
                "size": os.path.getsize(file_path),
                "path": file_path
            })
    
    return {"files": files}


@api.get("/task/{task_id}/download/{filename}")
async def download_file(task_id: str, filename: str):
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    output_dir = running_tasks[task_id].get("output_dir", "")
    if not output_dir:
        raise HTTPException(status_code=404, detail="No output directory")
    
    file_path = os.path.join(output_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=filename)

@api.get("/task/{task_id}/download")
async def download_results(task_id: str):
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    output_dir = running_tasks[task_id].get("output_dir", "")
    if not output_dir or not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="No output directory")
    
    # 创建内存中的ZIP文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 遍历输出目录中的所有文件
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_dir)
                zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=autoba-results-{task_id[:8]}.zip"}
    )


class ThreadOutput:
    """线程安全输出包装器"""
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def write(self, text: str):
        if text.strip() and self.task_id in running_tasks:
            timestamp = datetime.now().isoformat()
            log_entry = {
                "time": timestamp,
                "message": text.strip(),
                "type": "stdout"
            }
            running_tasks[self.task_id]["logs"].append(log_entry)
    
    def flush(self):
        pass


async def run_autoba_task(task_id: str, goal: str, model_engine: str, openai_api: str, execute: bool, file_descriptions: str):
    """运行 AutoBA 任务"""
    
    def add_log(msg: str, msg_type: str = 'info'):
        if task_id in running_tasks:
            timestamp = datetime.now().isoformat()
            log_entry = {
                "time": timestamp,
                "message": msg,
                "type": msg_type
            }
            running_tasks[task_id]["logs"].append(log_entry)
            print(f"[{msg_type.upper()}] {msg}")
    
    try:
        running_tasks[task_id]["status"] = "running"
        
        add_log("=" * 60, 'system')
        add_log(f">>> AutoBA Task Started", 'system')
        add_log(f">>> Goal: {goal}", 'info')
        add_log(f">>> Model: {model_engine}", 'info')
        
        output_dir = os.path.join(AUTUBA_PATH, "output", f"task_{task_id[:8]}")
        os.makedirs(output_dir, exist_ok=True)
        running_tasks[task_id]["output_dir"] = output_dir
        add_log(f">>> Output Directory: {output_dir}", 'info')
        
        task_info = running_tasks.get(task_id)
        data_list = []
        
        if task_info and task_info.get("uploaded_files"):
            for f in task_info["uploaded_files"]:
                data_list.append(f)
        
        if file_descriptions:
            for line in file_descriptions.strip().split('\n'):
                if line.strip():
                    data_list.append(line.strip())
        
        data_list.append(f"{output_dir}: all outputs should be stored under this dir")
        
        add_log("=" * 60, 'system')
        add_log("Initializing AutoBA Agent...", 'info')
        
        original_dir = os.getcwd()
        
        try:
            os.chdir(AUTUBA_PATH)
            
            # 用于存储已输出的日志，避免重复
            log_history = set()
            
            def output_callback(text: str, stream_type: str = 'stdout'):
                # 避免日志重复输出
                # 清理日志内容，去除前缀和重复的标记
                clean_text = text
                
                # 去除可能的前缀
                if clean_text.startswith('[INFO] '):
                    clean_text = clean_text[7:]
                elif clean_text.startswith('[STDOUT] '):
                    clean_text = clean_text[9:]
                elif clean_text.startswith('[STDERR] '):
                    clean_text = clean_text[9:]
                elif clean_text.startswith('INFO: '):
                    clean_text = clean_text[6:]
                
                # 检查是否已经输出过相同的日志
                if clean_text not in log_history:
                    log_history.add(clean_text)
                    add_log(clean_text, stream_type)
            
            def run_agent():
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                
                try:
                    from src.agent import Agent
                    from src.executor import CodeExecutor
                    from src.data_precheck import DataPrecheck
                    
                    add_log(">>> Running data precheck...", 'info')
                    
                    # 提取上传的文件路径
                    uploaded_file_paths = []
                    if task_info and task_info.get("uploaded_files"):
                        for f in task_info["uploaded_files"]:
                            if f.startswith('/') or f.startswith('\\') or (len(f) > 1 and f[1] == ':'):
                                # 完整路径
                                file_path = f.split(':')[0].strip()
                                uploaded_file_paths.append(file_path)
                    
                    # 运行数据预检
                    precheck_results = DataPrecheck.precheck_all(uploaded_file_paths)
                    
                    # 检查预检结果
                    precheck_failed = False
                    for item, result in precheck_results.items():
                        if not result['status']:
                            add_log(f"!!! PRECHECK FAILED: {item} - {result['message']}", 'error')
                            precheck_failed = True
                        else:
                            add_log(f"✅ PRECHECK PASSED: {item} - {result['message']}", 'info')
                    
                    if precheck_failed:
                        add_log("!!! Data precheck failed, aborting task.", 'error')
                        if task_id in running_tasks:
                            running_tasks[task_id]["status"] = "failed"
                        return
                    
                    add_log(">>> Creating Agent instance...", 'info')
                    
                    agent = Agent(
                        initial_data_list=data_list,
                        output_dir=output_dir,
                        initial_goal_description=goal,
                        model_engine=model_engine,
                        openai_api=openai_api,
                        execute=execute,
                        blacklist='java,perl,annovar,Cutadapt,STAR',
                        gui_mode=False,
                        cpu=True,
                        rag=False
                    )
                    
                    # 保存agent实例以便后续控制
                    task_agents[task_id] = agent
                    
                    if hasattr(agent, 'code_executor'):
                        agent.code_executor.set_output_callback(output_callback)
                    
                    add_log(">>> Starting Agent execution...", 'info')
                    
                    # 重定向输出
                    sys.stdout = ThreadOutput(task_id)
                    sys.stderr = ThreadOutput(task_id)
                    
                    agent.run()
                    
                    add_log(">>> Agent execution completed!", 'success')
                    
                except Exception as e:
                    import traceback
                    add_log(f"!!! ERROR: {str(e)}", 'error')
                    for line in traceback.format_exc().split('\n'):
                        if line.strip():
                            add_log(f"    {line}", 'error')
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            
            thread = threading.Thread(target=run_agent, daemon=True)
            thread.start()
            
            # 等待线程完成
            while thread.is_alive():
                await asyncio.sleep(0.5)
            
            thread.join(timeout=60)
            
        finally:
            os.chdir(original_dir)
        
        if task_id in running_tasks:
            status = running_tasks[task_id].get("status", "pending")
            if status != "stopped" and status != "failed":
                running_tasks[task_id]["status"] = "completed"
                add_log("=" * 60, 'system')
                add_log(">>> TASK COMPLETED SUCCESSFULLY <<<", 'success')
                add_log("=" * 60, 'system')
        
    except Exception as e:
        import traceback
        add_log(f"!!! FATAL ERROR: {str(e)}", 'error')
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                add_log(f"    {line}", 'error')
        if task_id in running_tasks:
            running_tasks[task_id]["status"] = "failed"


if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8004, log_level="info")

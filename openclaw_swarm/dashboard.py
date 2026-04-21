"""
OpenClaw Swarm Dashboard - FastAPI Backend
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .memory import Memory
from .experience import ExperienceDB
from .swarm import SwarmCoordinator


# Initialize FastAPI
app = FastAPI(
    title="OpenClaw Swarm Dashboard",
    description="Web UI for managing OpenClaw Swarm",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
memory = Memory()
experience = ExperienceDB()
swarm = SwarmCoordinator(memory=memory, experience=experience)


# Request Models
class TaskRequest(BaseModel):
    task: str
    decompose: bool = True
    max_workers: int = 3


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - serve dashboard"""
    return {
        "name": "OpenClaw Swarm Dashboard",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/api/status")
async def get_status():
    """Get overall system status"""
    memory_stats = memory.get_stats()
    exp_stats = experience.get_stats()
    swarm_status = swarm.get_status()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "memory": memory_stats,
        "experience": exp_stats,
        "swarm": swarm_status
    }


@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get memory statistics"""
    return memory.get_stats()


@app.get("/api/memory/recent")
async def get_recent_memories(limit: int = 10):
    """Get recent memories"""
    all_memories = list(memory.memories.values())
    all_memories.sort(key=lambda x: x.timestamp, reverse=True)
    return all_memories[:limit]


@app.get("/api/memory/search")
async def search_memories(query: str, limit: int = 5):
    """Search memories"""
    return memory.find_similar(query, limit)


@app.delete("/api/memory/clear")
async def clear_memory(days: int = 30):
    """Clear old memories"""
    count = memory.clear_old(days)
    return {"cleared": count}


@app.get("/api/experience/stats")
async def get_experience_stats():
    """Get experience statistics"""
    return experience.get_stats()


@app.get("/api/experience/advice")
async def get_advice(task_type: str = "general"):
    """Get advice for a task type"""
    return experience.get_advice(task_type)


@app.get("/api/experience/lessons")
async def get_lessons(task_type: Optional[str] = None):
    """Get all lessons or filter by task type"""
    if task_type:
        return experience.get_lessons_for_task(task_type)
    else:
        return list(experience.lessons.values())


@app.get("/api/swarm/status")
async def get_swarm_status():
    """Get swarm status"""
    return swarm.get_status()


@app.get("/api/swarm/agents")
async def get_agents():
    """Get all agents"""
    return {
        agent_id: {
            "name": agent.name,
            "role": agent.role.value,
            "capabilities": agent.capabilities,
            "current_tasks": agent.current_tasks,
            "total_completed": agent.total_completed,
            "success_rate": agent.success_rate
        }
        for agent_id, agent in swarm.agents.items()
    }


@app.post("/api/swarm/run")
async def run_swarm_task(request: TaskRequest):
    """Run a swarm task"""
    try:
        result = swarm.run_swarm(
            task_description=request.task,
            max_workers=request.max_workers,
            decompose=request.decompose
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# Dashboard HTML (simple version)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Swarm Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        h1 { margin-bottom: 20px; color: #60a5fa; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
        .card h2 { color: #60a5fa; margin-bottom: 15px; font-size: 18px; }
        .stat { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #334155; }
        .stat-label { color: #94a3b8; }
        .stat-value { color: #22d3ee; font-weight: bold; }
        .btn { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #2563eb; }
        input, textarea { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 10px; border-radius: 8px; width: 100%; margin-bottom: 10px; }
        textarea { min-height: 100px; }
        .task-result { background: #0f172a; border-radius: 8px; padding: 15px; margin-top: 15px; white-space: pre-wrap; }
        #status { display: flex; gap: 20px; margin-bottom: 20px; }
        .status-item { background: #1e293b; padding: 15px 20px; border-radius: 8px; }
        .status-value { font-size: 24px; font-weight: bold; color: #22d3ee; }
        .status-label { font-size: 12px; color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>OpenClaw Swarm Dashboard</h1>
        
        <div id="status">
            <div class="status-item">
                <div class="status-value" id="total-memories">-</div>
                <div class="status-label">Memories</div>
            </div>
            <div class="status-item">
                <div class="status-value" id="total-experiences">-</div>
                <div class="status-label">Experiences</div>
            </div>
            <div class="status-item">
                <div class="status-value" id="success-rate">-</div>
                <div class="status-label">Success Rate</div>
            </div>
            <div class="status-item">
                <div class="status-value" id="active-agents">-</div>
                <div class="status-label">Agents</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>Run Task</h2>
                <textarea id="task-input" placeholder="Enter task description..."></textarea>
                <button class="btn" onclick="runTask()">Run Swarm</button>
                <div class="task-result" id="task-result"></div>
            </div>
            
            <div class="card">
                <h2>Memory</h2>
                <div id="memory-stats"></div>
            </div>
            
            <div class="card">
                <h2>Experience</h2>
                <div id="experience-stats"></div>
            </div>
            
            <div class="card">
                <h2>Agents</h2>
                <div id="agents-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadStatus() {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            document.getElementById('total-memories').textContent = data.memory.total_memories;
            document.getElementById('total-experiences').textContent = data.experience.total_experiences;
            document.getElementById('success-rate').textContent = (data.experience.success_rate * 100).toFixed(0) + '%';
            document.getElementById('active-agents').textContent = Object.keys(data.swarm.agents).length;
            
            // Memory stats
            const memDiv = document.getElementById('memory-stats');
            memDiv.innerHTML = `
                <div class="stat"><span class="stat-label">Total</span><span class="stat-value">${data.memory.total_memories}</span></div>
                <div class="stat"><span class="stat-label">Successful</span><span class="stat-value">${data.memory.successful}</span></div>
                <div class="stat"><span class="stat-label">Agents</span><span class="stat-value">${data.memory.agents}</span></div>
            `;
            
            // Experience stats
            const expDiv = document.getElementById('experience-stats');
            expDiv.innerHTML = `
                <div class="stat"><span class="stat-label">Total</span><span class="stat-value">${data.experience.total_experiences}</span></div>
                <div class="stat"><span class="stat-label">Success Rate</span><span class="stat-value">${(data.experience.success_rate * 100).toFixed(0)}%</span></div>
                <div class="stat"><span class="stat-label">Lessons</span><span class="stat-value">${data.experience.total_lessons}</span></div>
            `;
            
            // Agents list
            const agentsDiv = document.getElementById('agents-list');
            const agentsHTML = Object.entries(data.swarm.agents).map(([id, agent]) => `
                <div class="stat"><span class="stat-label">${agent.name}</span><span class="stat-value">${(agent.success_rate * 100).toFixed(0)}%</span></div>
            `).join('');
            agentsDiv.innerHTML = agentsHTML;
        }
        
        async function runTask() {
            const task = document.getElementById('task-input').value;
            if (!task) return;
            
            const resultDiv = document.getElementById('task-result');
            resultDiv.textContent = 'Running...';
            
            try {
                const response = await fetch('/api/swarm/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task: task, decompose: true })
                });
                const data = await response.json();
                resultDiv.textContent = data.final_result || JSON.stringify(data, null, 2);
                loadStatus();
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
            }
        }
        
        // Load on start
        loadStatus();
        setInterval(loadStatus, 5000);
    </script>
</body>
</html>
"""


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML"""
    return DASHBOARD_HTML


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the dashboard server"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
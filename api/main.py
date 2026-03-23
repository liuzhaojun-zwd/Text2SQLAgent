from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import sys
import json
import asyncio

# 确保能 import 到根目录的模块
# 动态将项目根目录（即 text_to_sql 的父目录 /root/data）加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from text_to_sql.agents.graph import create_agent_graph

app = FastAPI(title="Text-to-SQL API", description="基于 LangGraph 的企业级 Text-to-SQL 服务")

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中建议替换为具体的域名，如 ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化并编译 LangGraph 工作流
agent_workflow = create_agent_graph()

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    intent: Optional[str]
    generated_sql: Optional[str]
    final_response: str
    error_message: Optional[str]
    retry_count: int

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    接收用户的自然语言查询，运行完整的 Text-to-SQL LangGraph 工作流，并通过 SSE 流式返回节点状态。
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 初始化状态
    initial_state = {
        "user_query": request.query,
        "intent": None,
        "entities": [],
        "enhanced_query": None,
        "ddl_context": None,
        "generated_sql": None,
        "error_message": None,
        "execution_result": None,
        "retry_count": 0,
        "final_response": None
    }

    async def event_generator():
        try:
            print(f"🚀 收到流式请求: {request.query}")
            
            # 使用 .stream() 替代 .invoke()，实时获取每个节点的状态变化
            for output in agent_workflow.stream(initial_state):
                # LangGraph 的 stream 返回的是一个字典，键为当前执行完毕的节点名，值为更新后的 state
                for node_name, state_update in output.items():
                    event_data = {
                        "node": node_name,
                        "state_update": {
                            "intent": state_update.get("intent"),
                            "generated_sql": state_update.get("generated_sql"),
                            "error_message": state_update.get("error_message"),
                            "final_response": state_update.get("final_response")
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    # 给一小段缓冲时间，让前端感知到流式打字/状态流转效果
                    await asyncio.sleep(0.1)
                    
            # 结束标志
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"❌ 工作流执行异常: {e}")
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # 为了方便测试，直接在脚本内提供启动入口
    uvicorn.run(app, host="0.0.0.0", port=8000)

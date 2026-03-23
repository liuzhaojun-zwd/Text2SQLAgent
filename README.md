# Text2SQL 智能问答系统

本项目是一个基于大语言模型（LLM）的 Text2SQL 系统，旨在将自然语言准确地转换为 SQL 查询语句。

## 系统架构

本项目包含四大子系统闭环：
1. **Agent 编排**：使用 LangGraph DAG 拆解任务，流转各个原子节点。
2. **混合检索**：基于 Milvus 稠密检索与 BM25 稀疏检索结合，通过 RRF (Reciprocal Rank Fusion) 取 Top-10 结果。
3. **安全审计**：责任链 3 道闸，包括 SQL 预审和执行防护。
4. **执行运行**：沙箱执行，缓存结果与格式化输出。

### Agent 节点（DAG）
系统的执行流程：
用户输入 -> `intent_align` -> `schema_retriever` -> `sql_generator` -> `sql_auditor` -> `sql_executor` -> [失败] `reflection` ↻(最多3次) / [成功] `result_summary` -> 输出

### 召回机制 (Retrieval)
采用两阶段拓扑感知召回：
1. **混合召回**：
   - **稠密检索**：Sentence-BERT/BGE-M3 + Milvus IVF_FLAT (Top-20) 解决语义对齐、跨语言问题。
   - **稀疏检索**：BM25/SPLADE + 倒排索引 (Top-20) 保证字段名、枚举等精确命中。
   - **融合排序**：使用 RRF(k=60) 融合多路召回，取 Top-10 统一异构分数量纲。
2. **拓扑补全**：提取混合召回的核心表名后，进行外键一跳图谱查询，补齐核心表、关联表及外键的完整 DDL，实现拓扑感知。

## 技术栈

- **前端**：Vue3 + ElementPlus
- **后端**：FastAPI
- **关系型数据库**：MySQL
- **向量数据库**：Milvus
- **大语言模型 / Embedding**：智谱 AI GLM-4.7 模型
- **LLM 应用框架**：LangChain, LangGraph
- **容器化**：Docker (用于部署 Milvus 和 MySQL)

## 环境配置与依赖包

### 1. Python 依赖安装
本项目所需的环境包已锁定当前不报错的可用版本，并统一维护在 `pyproject.toml` 中。主要核心依赖包括：
- `langgraph >= 0.1.0`
- `langchain >= 0.2.0`
- `pymilvus == 2.5.3` (解决连接及列表数据类型不匹配的问题)
- `zhipuai` (智谱官方 SDK)
- `fastapi >= 0.110.0`
- `pymysql >= 1.1.0`

可直接在项目根目录下通过以下命令安装所有环境依赖：
```bash
pip install .
```

### 2. 环境变量及 API 密钥
- **ZhipuAI API Key**: ``

### 3. 数据库连接配置

**MySQL 数据库**
- 主机：`localhost`
- 端口：`3306`
- 数据库名：`text2sql`
- 用户名/密码：`root` / `123456`

**Milvus 向量数据库**
- 主机：`localhost`
- 端口：`19530`
- 数据库名：`text2sql`
- 用户名/密码：`root` / `123456`

> **常见问题排查**：如果在通过 Docker 部署 Milvus 时遇到连接超时 (`Timeout`) 或无效参数连接失败的情况，可能是本地代理干扰了容器网络通信。请在 `/root/.bashrc` 中清除代理环境变量来修复：
> ```bash
> export http_proxy=""
> export https_proxy=""
> source ~/.bashrc
> ```

## 启动项目

### 使用 Docker 部署 (推荐)

本项目依赖 MySQL 和 Milvus 数据库。你可以使用 Docker 快速拉起这些基础设施：

**1. 部署 MySQL**
```bash
docker run -d \
  --name text2sql-mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=text2sql \
  mysql:8.0
```

**2. 部署 Milvus (单机版)**
为了避免 Docker Hub 限制，你可以使用以下代理镜像拉取 Milvus 并启动（具体参考 Milvus 官方单机部署脚本或 docker-compose）：
```bash
# 下载官方 docker-compose.yml
wget https://github.com/milvus-io/milvus/releases/download/v2.4.9/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 如果网络受限，可修改 docker-compose.yml 中的 image 源，例如：
# image: docker.m.daocloud.io/milvusdb/milvus:v2.4.9

# 启动 Milvus
sudo docker-compose up -d
```

---

### 启动应用服务

本项目包含后端 (FastAPI) 和 前端 (Vue3)。

#### 1. 创建虚拟环境并安装依赖
建议在运行服务前创建虚拟环境：

```bash
cd /root/data/text_to_sql
# 创建虚拟环境
python3 -m venv .venv
# 激活虚拟环境
source .venv/bin/activate
# 升级 pip 并安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. 启动后端服务
在激活虚拟环境后，在项目根目录（`text_to_sql` 目录下）运行以下命令启动 FastAPI 服务：

```bash
cd /root/data/text_to_sql
PYTHONPATH=/root/data .venv/bin/python api/main.py
```
*或者使用 uvicorn 启动:*
```bash
cd /root/data/text_to_sql
PYTHONPATH=/root/data .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

启动成功后，API 服务默认运行在 `http://0.0.0.0:8000`。
你可以通过访问 `http://localhost:8000/docs` 查看并测试自动生成的 Swagger 接口文档。

#### 3. 启动前端界面 (Vue3)
前端使用 Vue3 + Vite 构建，并代理了对后端的跨域请求。

```bash
cd /root/data/text_to_sql/frontend
# 安装依赖 (首次运行需要)
npm install
# 启动开发服务器并暴露端口
npm run dev
```
启动成功后，您可以通过浏览器访问终端输出的地址（如 `http://localhost:5175` 或公网 IP 对应端口）来进行图形化交互测试。

#### 4. 后端接口调用示例
如果不使用前端界面，您也可以直接向 `/chat` 接口发送 POST 请求：

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"query": "查询研发部门有哪些员工"}'
```


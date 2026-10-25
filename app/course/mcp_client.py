"""独立MCP客户端：真实子进程、工具发现和协议调用；不伪造function-call结果。"""
import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.leave_web_accounts import DEMO_USERS, WEB_RUN_ID
from app.pgvector_store import PROJECT_ROOT


async def run_client(username: str, year: int=2026, run_id: str=WEB_RUN_ID) -> dict:
    if username not in {u['username'] for u in DEMO_USERS}:
        raise PermissionError('未知宿主用户')
    env={k:os.environ[k] for k in ('PATH','SYSTEMROOT','TEMP','TMP','PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSSLMODE') if k in os.environ}
    env.update(COURSE_MCP_USER=username,COURSE_MCP_RUN=run_id,PYTHONIOENCODING='utf-8')
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','app.course.mcp_server'],env=env,cwd=str(PROJECT_ROOT))
    async with stdio_client(params) as (reader,writer):
        async with ClientSession(reader,writer) as session:
            await session.initialize()
            found=await session.list_tools()
            result=await session.call_tool('get_my_leave_balance',{'year':year})
            rejected=await session.call_tool('get_my_leave_balance',{'year':year,'user_id':'web-zhaoliu'})
            if not rejected.isError:
                raise AssertionError('多余身份参数未被拒绝')
            return {'transport':'stdio','sdk_line':'mcp-v1.30','tools':[t.name for t in found.tools],
                    'result':result.model_dump(mode='json'),'extra_identity_rejected':rejected.isError,'model_called':False}


def run_sync(username: str, year: int=2026, run_id: str=WEB_RUN_ID) -> dict:
    return asyncio.run(asyncio.wait_for(run_client(username,year,run_id),timeout=25))

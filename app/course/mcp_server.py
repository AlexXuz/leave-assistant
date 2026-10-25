"""MCP SDK v1.30 stdio服务；进程启动身份由宿主注入，工具参数不能指定用户。"""
import os
from mcp.server.fastmcp import FastMCP

from app.leave_web_accounts import DEMO_USERS, WEB_RUN_ID, account_balance, initialize_accounts
from app.pgvector_store import connect_database

username=os.environ.get('COURSE_MCP_USER','')
if username not in {u['username'] for u in DEMO_USERS}:
    raise RuntimeError('宿主必须注入已认证的演示账号')
USER_ID='web-'+username
RUN_ID=os.environ.get('COURSE_MCP_RUN',WEB_RUN_ID)
if RUN_ID!=WEB_RUN_ID and not RUN_ID.startswith('day12-web-check-'):
    raise RuntimeError('不允许的教学命名空间')
class StrictMCP(FastMCP):
    """v1 FastMCP默认忽略多余参数；显式收紧公开调用入口与发现Schema。"""
    async def list_tools(self):
        tools=await super().list_tools()
        for tool in tools:
            tool.inputSchema['additionalProperties']=False
        return tools

    async def call_tool(self,name,arguments):
        allowed={'get_my_leave_balance':{'year'},'list_my_applications':{'limit'}}
        if name in allowed and set(arguments)-allowed[name]:
            raise ValueError('不接受额外参数；身份只能来自宿主')
        return await super().call_tool(name,arguments)


mcp=StrictMCP('leave-readonly-course')


@mcp.tool()
def get_my_leave_balance(year: int) -> dict:
    """读取当前宿主绑定用户的年度年假余额；不能传入员工ID或修改余额。"""
    if type(year) is not int or not 2000<=year<=2100:
        raise ValueError('年份无效')
    with connect_database() as c, c.transaction():
        c.execute('SET TRANSACTION READ ONLY')
        value=account_balance(c,RUN_ID,USER_ID,year)
    return {'status':'ok' if value else 'not_found','balance':value,'scope':'current_host_user'}


@mcp.tool()
def list_my_applications(limit: int=5) -> dict:
    """只读取当前用户最近的待审批申请。"""
    if type(limit) is not int or not 1<=limit<=20:
        raise ValueError('条数应为1至20')
    with connect_database() as c, c.transaction():
        c.execute('SET TRANSACTION READ ONLY')
        rows=c.execute('SELECT application_id,status,requested_days FROM leave_workflow_lab.applications WHERE run_id=%s AND user_id=%s ORDER BY application_id LIMIT %s',(RUN_ID,USER_ID,limit)).fetchall()
    return {'applications':rows,'scope':'current_host_user'}


if __name__=='__main__':
    with connect_database() as c:
        initialize_accounts(c,RUN_ID)
    mcp.run(transport='stdio')

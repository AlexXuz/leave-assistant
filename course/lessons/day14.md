# Day14 · MCP把工具连接标准化，但不会替你做授权

目标：启动一个独立MCP进程，用另一个客户端发现并调用工具，观察请求Schema、协议结果与业务数据三层结构。

## 与Tool Calling的关系

Day10中，模型生成工具名和参数，你的后端执行Python函数。MCP解决的是客户端与工具服务如何发现能力、传递参数和返回结果。模型仍需要决定是否用工具，宿主仍需要绑定身份，服务端仍需要校验权限。没有模型，也能用MCP客户端直接调用；这正是本课首先验证的链路。

本课锁定 `mcp==1.30.0` 的v1 API：FastMCP、ClientSession、stdio_client。MCP SDK v2存在不同的API与协议行为，不应复制当前网上main分支示例混用。本课版本和入口已记录在requirements-course.txt。

## 三个角色在本项目的位置

- 宿主：已登录的课程Web服务，知道当前是张三还是李四。
- 客户端：`app/course/mcp_client.py`，创建子进程、初始化、list_tools、call_tool。
- 服务端：`app/course/mcp_server.py`，暴露get_my_leave_balance和list_my_applications。

宿主把账号通过子进程环境注入。模型工具参数只有year或limit，不能提交user_id。stdio模式的进程属于宿主信任边界，这不是远程OAuth认证示范。部署远程Streamable HTTP服务时，必须重新落实认证、令牌验证、授权范围和Origin检查，不能把固定环境变量直接当作公网身份。

## 读懂一次结果

工具发现返回inputSchema。工具调用返回可能含structuredContent或文本content，也有isError。协议调用成功不代表业务有记录：status=not_found仍是业务上的“查无记录”，不能改为0。isError=true更不能被包装成余额查询成功。

作业函数 `decode_tool_result(result)`：先检查isError；优先structuredContent；否则只拼接text类型的内容并解析JSON；最后验证status只可能ok/not_found。输入结构和输出契约在 `course/assignments/mcp_result_parser.py`。

## 实际遇到的SDK细节

本次验证发现v1 FastMCP默认会忽略额外参数。仅在Schema中不列出user_id，并不自动等于运行时拒绝它。参考服务使用公开call_tool入口增加允许参数集合校验，并给发现Schema补additionalProperties=false。即使没有这层拒绝，身份也绝不能从额外参数取；现在两层都落实。

## 页面操作与验收

登录任一账号，打开MCP实验，点击“发现并调用”。应看到transport=stdio、两个真实工具名、当前账号余额和extra_identity_rejected=true。切换账号再调用，数据应对应新账号。观察服务日志：标准输出用于协议消息，业务调试日志应去stderr，否则会破坏stdio传输。

验收记录必须包含独立进程发现/调用结果，不能只是本地直接调用同名Python函数。失败排查：初始化失败先看进程环境和解释器；JSON解析失败先区分协议content和业务JSON；返回他人数据查身份绑定；超时应停止并清理子进程，不无限重启。

来源：[MCP Python SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)。参考解码函数在 `course/solutions/mcp_result_parser.py`，客户端和服务端已可运行。

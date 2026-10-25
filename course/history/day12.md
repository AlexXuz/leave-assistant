# Day12 状态编排、暂停与恢复

后续更新：2026-10-25学习者要求一次性准备剩余课程。完整自学讲解已放在 [course/lessons/day12.md](../lessons/day12.md)，入口 [course/README.md](../README.md)。LangGraph参考图、持久检查点和页面暂停/恢复实验现已实现并验证；下文保留此前逐课准备历史。学习者自己的路由作业未被参考答案覆盖，个人完成状态仍待本人验收。

2026-10-25开课。Day11完整业务链路已通过；根据学习者要求，后续以网页操作为主要体验入口，命令行检查保留作回归与排障。助教负责页面/API脚手架，学习者继续实现核心业务/编排函数。

## 页面入口

本机 http://127.0.0.1:8012 。独立应用app/leave_web.py不改Day1的app/main.py。页面使用真实DeepSeek提取和Day11的PostgreSQL预检、确认及提交函数；不是预设成功动画。确认与提交为两个明确按钮，刷新/重启后可读取原结果，重复提交复用服务端保存的key。

页面当前运行Day11的Python编排，尚未接入LangGraph。没有把按钮显示“等待确认”冒充interrupt或检查点。2026-10-25根据学习者体验反馈，已把最初“每草稿独立余额”的临时页面改为演示账号登录和共享持久额度：同一账号的全部草稿和申请共享同一年度账户；登录、刷新或服务重启不重置可用/预占/已用天数。账号、会话、余额、草稿及请求key均存PostgreSQL，初始化只补不存在的记录，不覆盖已有额度。

演示账号密码均为demo123：zhangsan（张三/研发，初始年假可用9天）、lisi（李四/财务，3天）、wangwu（王五/运营，0天）、zhaoliu（赵六/产品，15天）。均配置2026年账户。页面顶部显示当前登录人、年度及年假可用/预占/已用。账号各自查询本人历史、确认和提交；身份从后端登录会话读取，模型/请求JSON不得指定user_id。密码以加盐PBKDF2摘要保存，Cookie为HttpOnly/SameSite，数据库只保存会话令牌摘要，退出撤销当前会话。同源写入校验保留。本机固定公开演示密码不用于生产认证或公网部署。

旧版SQLite浏览器映射及独立SQL演示记录保留，不导入新账号，不清空旧学习记录。当前仅开放整天年假。事假/病假显示LEAVE_TYPE_UNSUPPORTED的明确原因，草稿不显示不适用的年假数值；年假账户概览仍独立显示。没有修改学习者已验收的年假预检、确认或提交函数来放宽规则。

启动（Docker/PostgreSQL需已就绪）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.leave_web:app --host 127.0.0.1 --port 8012 --reload
```

在网页依次：描述四天年假→生成草稿→核对→确认→提交→刷新。日期不完整时停在补充信息；业务不支持或余额不足时不出现确认/提交按钮。提交后显示待审批、申请编号和可用/预占/已使用天数。提交后的页面说明由确定性字段生成，不额外消耗模型请求；模型不会决定提交是否成功。

可体验：张三申请四天年假后可用9→5；再申请四天后5→1；新草稿不会重置成9天。同一key重试不重复预占。李四申请四天会因只有3天而被阻止；王五可体验0额度；赵六用于额度较充足的情形。年假余额按账户共享，因此其他已预检草稿的额度可能变化，提交时继续执行学习者函数的最新余额复查。

## 第一题 只决定下一步 待实现

编辑app/leave_graph_routing.py中的route_leave_workflow。输入LeaveRouteState是有类型的服务端状态：draft_status、missing_fields、application_id。输出NextNode是允许的下一节点名。

此函数相当于条件边：判断该去哪里，不执行那个节点。譬如CONFIRMED应返回submit，而不是在函数里直接提交；READY_FOR_CONFIRMATION应返回wait_confirmation，不能替用户确认。先处理已经提交的事实，再处理缺信息、业务阻止与可继续的状态。完整顺序及不一致状态的拒绝规则见docstring。

写完刷新页面，展开“学习观察”，点击“检查我的路由”。接口从真实数据库构造输入，不接收浏览器伪造的状态；只展示选择的next_node，executed=false。本题尚未实现时返回明确501，不影响正常请假操作。

## 当前脚手架验证

2026-10-25助教运行scripts.check_leave_web：真实PostgreSQL、固定模型响应，检查未确认拒绝提交、严格版本输入、确认不占额度、提交待审批、同key复用、浏览器归属隔离、跨站拒绝及重建应用后读取状态。通过报告reports/leave-web-check-20261025-111033-021366.json，检查创建的SQL会话已清理。此前一次检查业务断言通过但Windows临时文件清理失败，修正SQLite连接显式关闭后复验；旧报告明确记failed，不能作为全部通过证据。

随后助教在实际浏览器通过页面按钮完成真实DeepSeek提取→确认→提交→刷新，报告依次为reports/leave-web-prepare-20261025-111116-035474.json、reports/leave-web-confirm-20261025-111128-952939.json、reports/leave-web-submit-20261025-111131-936091.json；同一申请application-69363de641be4aa2ba73311eda4fc0c3保持待审批，可用5/预占4/已用0。该浏览器教学记录保留供学习者查看，操作者为助教，不能当作学习者路由题已完成。页面截图为ignored目录tmp/leave-web-proof.png。当前第一题仍为NotImplementedError。

上述为旧版临时页面的历史证据。改为账号后，scripts.check_leave_web更新为隔离run_id中的四账号真实SQL验证，固定模型响应，不占用学习者四个演示账户。通过报告reports/leave-web-accounts-check-20261025-112929-988431.json：9→5→1共享额度、重复提交只占一次、第二草稿可见最新余额、余额不足及0余额拒绝、事假不冒用年假余额、账号历史隔离、伪造身份和跨账号读取/提交拒绝、退出令牌失效、应用重建及重新登录后额度/申请编号保持。测试数据已清理。实际演示账号仍保持初始9/3/0/15天可用额度供学习者操作。

助教另在浏览器实际点击张三账号卡片登录，核对本人身份、年假可用9/预占0/已用1，随后退出并刷新，回到四账号登录页；未为这次UI验证提交真实演示账号的申请。截图tmp/leave-account-balance.png、tmp/leave-accounts-login.png。模型日志适配器捕获stdout的部分用单进程锁串行化，避免并行请求混淆用量记录，SQL事务中没有模型网络调用。

## 原后续学习任务（参考实现现已备好，待本人学习）

1. 用StateGraph连接已有节点，第一题作为条件路由。明确State是工作快照、Node执行一步、Edge决定下一步。
2. 使用interrupt在确认前暂停，并用同一个thread_id和Command(resume=...)恢复；后端仍验证身份、版本、内容和服务端确认，图状态不能替代业务授权。
3. 接入持久检查点，验证刷新/服务重启恢复、节点失败重试和执行上限。interrupt恢复时节点从头执行，暂停之前不能放未经幂等保护的提交副作用。

参考：
- https://docs.langchain.com/oss/python/langgraph/graph-api
- https://docs.langchain.com/oss/python/langgraph/interrupts

Day12未完成，不提交为已完成Day。

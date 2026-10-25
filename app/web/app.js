const $ = id => document.getElementById(id);
let current = null, busy = false, items = [], me = null;
const labels = {READY_FOR_CONFIRMATION:'待你确认',CONFIRMED:'已确认 · 待提交',SUBMITTED:'已提交 · 待审批',BLOCKED:'暂不能申请',NEEDS_ASSESSMENT:'待补充信息'};
const fields = {leaveType:'假期类型',startDate:'开始日期',endDate:'结束日期',reason:'请假事由'};
function notice(message=''){const target=me?$('notice'):$('login-notice');target.textContent=message;target.hidden=!message;}
async function api(path,body){
  const response=await fetch(path,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok){const error=Error(typeof data.detail==='string'?data.detail:'输入未通过检查，请核对后重试。');error.status=response.status;throw error;}
  return data;
}
function showLogin(){me=null;current=null;items=[];$('workspace-ui').hidden=true;$('login-screen').hidden=false;$('password').value='';$('request').value='';$('route-result').textContent='';render(null);history();}
function account(data){
  me=data;$('workspace-ui').hidden=false;$('login-screen').hidden=true;
  const person=data.user,b=data.balance;
  $('profile-name').textContent=person.display_name;$('profile-department').textContent=person.department+' · '+person.username;
  $('avatar').textContent=person.display_name[0];$('header-user').textContent=person.display_name+' / '+person.department;
  $('account-year').textContent=(b?.year||2026)+' 年假账户';
  $('account-available').textContent=b?.remaining_days??'—';$('account-reserved').textContent=b?.reserved_days??'—';$('account-used').textContent=b?.used_days??'—';
}
async function refreshAccount(){account(await api('/api/me'));}
function render(view){
  current=view;$('empty').hidden=!!view;$('detail').hidden=!view;$('route').disabled=!view||busy;
  $('status').textContent=view?labels[view.draft_status]:'等待输入';
  for(let i=1;i<=3;i++)$('step'+i).classList.toggle('current',i===(view?(view.confirmed?3:2):1));
  if(!view){$('raw').textContent='尚未生成草稿';return;}
  const d=view.draft;
  $('type').textContent={ANNUAL:'年假',SICK:'病假',PERSONAL:'事假'}[d.leaveType]||'待补充';
  $('start').textContent=d.startDate||'待补充';$('end').textContent=d.endDate||'待补充';$('reason').textContent=d.reason||'待补充';
  const days=d.startDate&&d.endDate?(Date.parse(d.endDate)-Date.parse(d.startDate))/86400000+1:null;
  $('days').textContent=days>0?days+' 天':'待确定';
  for(const[id,key]of[['available','remaining_days'],['reserved','reserved_days'],['used','used_days']])$(id).textContent=view[key]??'—';
  $('draft-balances').hidden=d.leaveType!=='ANNUAL';
  $('draft-balance-label').textContent=d.leaveType==='ANNUAL'?(view.balance_year||'申请年度')+' 年假账户当前额度':'此假种暂未开放，没有使用年假额度校验；你的年假余额见顶部账户。';
  const reasonMessages={LEAVE_TYPE_UNSUPPORTED:'当前仅开放年假申请，事假、病假尚未开放。这不是余额不足，请改为年假体验或等待后续扩展。',CROSS_YEAR_UNSUPPORTED:'暂不支持跨年度申请，请按年度拆分安排。',INSUFFICIENT_BALANCE:'当前年假可用额度不足。请调整请假天数，或切换其他演示账号体验。',BALANCE_UNAVAILABLE:'该申请年度没有可靠的年假余额记录，暂不能提交。演示账号已配置2026年度额度。'};
  const messages={READY_FOR_CONFIRMATION:'草稿已整理，预检通过。请核对信息后确认，此时尚未提交。',CONFIRMED:'你已确认此版本。点击提交后才会创建申请并预占额度。',SUBMITTED:'已提交成功，申请正在等待审批。',BLOCKED:reasonMessages[view.assessment?.code]||'当前申请未通过业务校验，请核对需求后重新生成。',NEEDS_ASSESSMENT:'还需要补充：'+view.missing_fields.map(x=>fields[x]||x).join('、')+'。请在左侧写完整需求，重新生成草稿。'};
  const staleBalance=['READY_FOR_CONFIRMATION','CONFIRMED'].includes(view.draft_status)&&view.assessment?.status==='BLOCKED';
  $('draft-message').textContent=staleBalance?'账户余额已变化：'+(reasonMessages[view.assessment.code]||'请重新生成草稿。'):messages[view.draft_status];
  $('confirm').hidden=view.draft_status!=='READY_FOR_CONFIRMATION'||staleBalance;$('submit').hidden=view.draft_status!=='CONFIRMED'||staleBalance;
  $('application').hidden=!view.application;$('application-id').textContent=view.application?.application_id||'';
  $('version').textContent='草稿版本 '+view.revision;$('raw').textContent=JSON.stringify(view,null,2);
}
function history(){
  $('history').replaceChildren();
  if(!items.length){const p=document.createElement('p');p.className='muted';p.textContent='此账号暂无申请';$('history').append(p);}
  for(const view of items){
    const button=document.createElement('button');button.disabled=busy;button.classList.toggle('selected',view.draft_id===current?.draft_id);
    const title=document.createElement('span');title.textContent=(view.draft.startDate||'日期待定')+' · '+({ANNUAL:'年假',SICK:'病假',PERSONAL:'事假'}[view.draft.leaveType]||'待完善');
    const sub=document.createElement('small');sub.textContent=labels[view.draft_status];button.append(title,sub);
    button.onclick=()=>work(async()=>{render(await api('/api/drafts/'+view.draft_id));history();});$('history').append(button);
  }
}
function cache(view){items=[view,...items.filter(v=>v.draft_id!==view.draft_id)];render(view);history();}
async function work(action){
  if(busy)return;busy=true;notice();document.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{await action();}catch(error){if(error.status===401&&me)showLogin();notice(error instanceof TypeError?'连接中断，请先刷新页面核对状态。已经提交的申请不会因为刷新而重复占用额度。':error.message);}
  finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);$('route').disabled=!current;history();}
}
$('login-form').onsubmit=event=>{event.preventDefault();work(async()=>{await api('/api/login',{username:$('username').value.trim(),password:$('password').value});current=null;items=[];await load();$('password').value='';});};
$('logout').onclick=()=>work(async()=>{await api('/api/logout',{});showLogin();await loadDemoAccounts();});
$('account-refresh').onclick=()=>work(load);
$('prepare').onclick=()=>work(async()=>{
  const text=$('request').value.trim();if(!text)throw Error('先写下你的请假需求，或者点击上面的示例。');$('prepare').textContent='正在整理…';
  try{cache(await api('/api/drafts',{text}));await refreshAccount();$('route-result').textContent='';document.querySelector('.draft').scrollIntoView({behavior:'smooth',block:'start'});}finally{$('prepare').textContent='整理申请草稿 ↗';}
});
$('confirm').onclick=()=>work(async()=>{cache(await api('/api/drafts/'+current.draft_id+'/confirm',{revision:current.revision}));await refreshAccount();});
$('submit').onclick=()=>work(async()=>{cache(await api('/api/drafts/'+current.draft_id+'/submit',{revision:current.revision}));await refreshAccount();});
$('refresh').onclick=()=>work(async()=>{cache(await api('/api/drafts/'+current.draft_id));await refreshAccount();});
$('reload').onclick=()=>work(load);
$('route').onclick=()=>work(async()=>{$('route-result').textContent=JSON.stringify(await api('/api/drafts/'+current.draft_id+'/route-preview',{}),null,2);});
 document.querySelectorAll('[data-example]').forEach(button=>button.onclick=()=>{$('request').value=button.dataset.example;$('request').focus();});
async function load(){await refreshAccount();items=await api('/api/drafts');if(current){render(items.find(v=>v.draft_id===current.draft_id)||null);}else render(items[0]||null);history();}
async function loadDemoAccounts(){
  const data=await api('/api/demo-accounts');$('demo-accounts').replaceChildren();$('demo-password').textContent='全部演示账号密码：'+data.password+'。卡片显示初始可用额度，实际余额以登录后为准。';
  for(const person of data.accounts){const button=document.createElement('button');button.type='button';const name=document.createElement('b');name.textContent=person.display_name+' · '+person.department;const user=document.createElement('span');user.textContent=person.username;const quota=document.createElement('small');quota.textContent=data.year+'年初始可用 '+person.initial_available+' 天年假';button.append(name,user,quota);button.onclick=()=>{$('username').value=person.username;$('password').value=data.password;document.querySelectorAll('.demo-accounts button').forEach(b=>b.classList.toggle('selected',b===button));};$('demo-accounts').append(button);}
}
work(async()=>{await loadDemoAccounts();try{await load();}catch(error){if(error.status===401)showLogin();else throw error;}});

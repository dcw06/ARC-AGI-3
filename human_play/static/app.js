'use strict';
const $ = id => document.getElementById(id);
const names = {0:'重置',1:'↑ 向上',2:'↓ 向下',3:'← 向左',4:'→ 向右',5:'空格动作',6:'点击',7:'Z 撤销'};
let games = [], palette = [], selected = 'ar25', session = null, busy = false, animating = false, animation = 0;
let toastTimer, lastFrames = [], started = 0;
let displayedFrame = null, regionCorners = [], regionSequence = null, regionSession = null;
let ls20Guide=null,guideLoading=false;
const canvas = $('board'), context = canvas.getContext('2d');
function message(text) { $('error').textContent = text; $('error').hidden = !text; }
function toast(text) { $('toast').textContent=text; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>{$('toast').hidden=true;},2500); }
async function api(path, data) {
  const options = data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Arc-Play':'1'},body:JSON.stringify(data)};
  let response;
  try { response=await fetch(path,options); } catch { throw new Error('连接中断。日志已保存到本机；请确认服务仍在运行，然后刷新。'); }
  const value=await response.json();
  if(!response.ok) throw new Error(value.error || '本地服务暂时无法处理请求。');
  return value;
}
function download(zip=false, id=session?.session_id) {
  if(!id) return;
  const a=document.createElement('a'); a.href=`/api/sessions/${id}/download${zip?'.zip':''}`; a.download='';
  document.body.append(a); a.click(); a.remove();
}
function draw(frame) {
  if(!frame?.length) return;
  displayedFrame=frame;
  canvas.width=frame[0].length; canvas.height=frame.length;
  for(let y=0;y<frame.length;y++) for(let x=0;x<frame[y].length;x++) {
    context.fillStyle=palette[frame[y][x]] || '#ff00ff'; context.fillRect(x,y,1,1);
  }
}
async function animate(frames) {
  const ticket=++animation; animating=true; renderControls();
  // Display at most ~1 second of animation; all original frames remain in the log.
  const stride=Math.max(1,Math.ceil(frames.length/30));
  for(let i=0;i<frames.length-1;i+=stride) {
    if(ticket!==animation) return;
    draw(frames[i]); await new Promise(resolve=>setTimeout(resolve,35));
  }
  if(ticket===animation) { draw(frames.at(-1)); animating=false; renderControls(); }
}
function renderGames() {
  $('games').replaceChildren();
  games.forEach((g,i)=>{
    const button=document.createElement('button');button.className='game-option'+(g.id===selected?' selected':'');
    button.setAttribute('aria-pressed',String(g.id===selected));button.setAttribute('aria-label',`选择游戏 ${g.id}`);
    const index=document.createElement('span');index.className='game-index';index.textContent=String(i+1).padStart(2,'0');
    const code=document.createElement('span');code.className='code';code.textContent=g.id;
    const marker=document.createElement('span');marker.className=g.ready?'game-marker':'offline';marker.textContent=g.ready?'':'未下载';
    button.append(index,code,marker);button.addEventListener('click',()=>choose(g.id));$('games').append(button);
  });
}
function renderControls() {
  const obs=session?.observation;
  const locked=!session || busy || animating || session.closed || session.uncertain || obs?.state==='WIN' || $('annotation-mode').checked;
  document.querySelectorAll('[data-action]').forEach(b=>{
    const action=Number(b.dataset.action);
    b.disabled=locked || (action!==0 && (!obs.available_actions.includes(action) || obs.state==='GAME_OVER'));
  });
  $('download').disabled=!session || busy;
  $('save-note').disabled=!session || busy;
  $('finish').disabled=!session || busy || session.closed;
  $('start').disabled=busy || !games.find(g=>g.id===selected)?.ready;
  $('new-round').disabled=busy;
  $('save-region').disabled=!session || busy || animating || session.uncertain || regionCorners.length!==2;
  $('replay').disabled=!session || busy || animating || !lastFrames.length;
  canvas.setAttribute('aria-busy',String(busy || animating));
}
function renderSession(animateFrame=false) {
  animation++;animating=false;
  hideCoordinates();
  renderGuide();
  if(!session || regionSequence!==session.sequence || regionSession!==session.session_id) clearRegion();
  $('annotations').replaceChildren();
  for(const event of session?.annotations || []){
    const r=event.region,b=r.bounds_inclusive,li=document.createElement('li');
    li.textContent=`${r.name} · ${r.cell_count} 格 · 第 ${r.sequence} 步\nx ${b.x_min}–${b.x_max}, y ${b.y_min}–${b.y_max}`;
    $('annotations').append(li);
  }
  const obs=session?.observation;
  $('welcome').hidden=!!session;
  $('breadcrumb-game').textContent=selected;$('game-title').textContent=selected;
  $('official-link').href=`https://arcprize.org/tasks/${selected}`;
  $('start').textContent=`开始 ${selected} →`;
  $('levels').textContent=obs?.levels_completed ?? 0;$('total-levels').textContent=obs?.win_levels ?? '—';
  $('actions').textContent=session?.sequence ?? 0;
  const state=!session?'未开始':session.uncertain?'结果待确认':session.closed?'已结束':obs.state==='WIN'?'已通关':obs.state==='GAME_OVER'?'需重置':'探索中';
  $('state-label').textContent=state;$('game-badge').textContent=state;
  $('board-status').replaceChildren();const dot=document.createElement('span');dot.className='status-dot';$('board-status').append(dot,state==='未开始'?'等待你的第一步':state);
  $('level-dots').replaceChildren();
  for(let i=0;i<(obs?.win_levels || 0);i++){const d=document.createElement('span');d.className=i<obs.levels_completed?'complete':i===obs.levels_completed?'current':'';$('level-dots').append(d);}
  $('save-status').textContent=session?`已自动保存 · ${session.session_id.slice(0,8)}`:'开始后自动保存到本机';
  $('click-hint').textContent=obs?.available_actions.includes(6)?'可点击画面交互。坐标从左上角 (0, 0) 开始；每一步返回后可继续操作。':'本游戏使用键盘／亮起的按键。未开放的动作不会发送给引擎。';
  $('completion').hidden=!(session && (obs.state==='WIN' || session.closed || session.uncertain));
  $('completion-title').textContent=session?.uncertain?'上一步结果待确认':obs?.state==='WIN'?'全部关卡完成，做得好！':'本轮探索已保存';
  $('completion-text').textContent=session?.uncertain?'请先下载日志，再新开一轮；不会把未知结果当作没变化。':'完整的动作、画面与观察笔记，都可以下载。';
  $('history').replaceChildren();
  if(!session?.history.length){const li=document.createElement('li');li.className='empty-copy';li.textContent='你的探索会出现在这里。';$('history').append(li);}
  for(const event of [...(session?.history || [])].reverse()){
    const li=document.createElement('li'),n=document.createElement('span'),a=document.createElement('span'),l=document.createElement('small');
    n.textContent=String(event.sequence).padStart(2,'0');a.textContent=names[event.action.action_id];
    if(event.action.action_id===6)a.textContent+=` (${event.action.action_data.x}, ${event.action.action_data.y})`;
    l.textContent=event.status==='acknowledged'?`通过 ${event.levels_completed} 关`:'结果未知';li.append(n,a,l);$('history').append(li);
  }
  started=session?Date.parse(session.started_at):0;
  if(obs){lastFrames=obs.frames; if(animateFrame) void animate(lastFrames); else draw(lastFrames.at(-1));}
  else {animation++;animating=false;context.clearRect(0,0,canvas.width,canvas.height);lastFrames=[];}
  renderGames();renderControls();
}
async function choose(code) {
  if(busy || code===selected) return;
  // Previous rounds stay on the server and in Recent Explorations.
  selected=code;session=null;localStorage.removeItem('arc-human-session');message('');renderSession();
}
async function start() {
  if(busy) return;
  if(session && !session.closed && session.observation.state!=='WIN' && !confirm('新开一轮？当前记录仍会保留，可从“最近的探索”继续或下载。')) return;
  busy=true;message('');renderControls();
  try {
    session=await api('/api/sessions',{game_id:selected,seed:0});
    localStorage.setItem('arc-human-session',session.session_id);$('note').value='';$('note-status').textContent='留住此刻的想法';
    renderSession(true);await recent();canvas.focus({preventScroll:true});
  } catch(error) { message(error.message); }
  finally {busy=false;renderControls();}
}
async function action(id,coords={}) {
  if(!session || busy || animating) return;
  if(id===0 && session.sequence && !confirm('重置当前关卡？这一步也会计入日志。引擎在特殊状态下可能重置整个游戏。')) return;
  busy=true;message('');renderControls();
  try {
    const oldLevel=session.observation.levels_completed;
    session=await api(`/api/sessions/${session.session_id}/action`,{action_id:id,...coords,event_id:crypto.randomUUID(),expected_sequence:session.sequence});
    renderSession(true);
    if(session.observation.levels_completed>oldLevel)toast(`通过第 ${session.observation.levels_completed} 关！`);
    canvas.focus({preventScroll:true});
  } catch(error) { message(error.message); }
  finally {busy=false;renderControls();}
}
async function recent() {
  try {
    const data=await api('/api/sessions');$('recent').replaceChildren();
    if(!data.sessions.length){const span=document.createElement('span');span.className='empty-copy';span.textContent='还没有记录，开始你的第一轮吧。';$('recent').append(span);}
    data.sessions.slice(0,8).forEach(row=>{
      const card=document.createElement('div');card.className='recent-session';
      const resume=document.createElement('button');resume.className='resume';resume.textContent=`${row.short_id} · ${new Date(row.started_at).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})}`;
      resume.addEventListener('click',()=>restore(row.session_id));
      const link=document.createElement('a');link.textContent='↓';link.title='下载这轮日志';link.href=`/api/sessions/${row.session_id}/download`;link.setAttribute('download','');card.append(resume,link);$('recent').append(card);
    });
  } catch(error) { message(error.message); }
}
async function restore(id) {
  if(busy)return;busy=true;renderControls();message('');
  try {session=await api(`/api/sessions/${id}`);selected=session.short_id;localStorage.setItem('arc-human-session',id);renderSession();toast('已恢复这轮探索');}
  catch(error){message(error.message);localStorage.removeItem('arc-human-session');}
  finally{busy=false;renderControls();}
}
$('start').addEventListener('click',start);$('new-round').addEventListener('click',start);
$('download').addEventListener('click',()=>download());$('completion-download').addEventListener('click',()=>download());
$('refresh-recent').addEventListener('click',recent);$('replay').addEventListener('click',()=>void animate(lastFrames));
document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>action(Number(b.dataset.action))));
function renderGuide(){
  $('ls20-guide').hidden=selected!=='ls20' || (session && session.observation.levels_completed!==0);
  if($('ls20-guide').hidden)return;
  if(!ls20Guide){
    if(!guideLoading){guideLoading=true;api('/ls20-level1.json').then(data=>{ls20Guide=data;renderGuide();}).catch(error=>{$('ls20-objects').textContent=error.message;}).finally(()=>{guideLoading=false;});}
    return;
  }
  $('ls20-objects').replaceChildren();
  const roles={controlled_object:'受控物体',target:'目标',interaction_marker:'交互标记',obstacle:'障碍',walkable_path:'通路',boundary_candidate:'边界候选',interface_shape_indicator:'形状提示',interface_progress_bar:'状态条',interface_indicator:'界面指示'};
  const statuses={action_verified:'动作验证',completion_verified:'过关验证',collision_verified:'碰撞验证',path_verified:'路径验证',change_observed:'观察到变化',partly_tested:'部分测试',unverified:'作用待验证'};
  for(const o of ls20Guide.objects){
    const entry=document.createElement('details'),name=document.createElement('summary'),body=document.createElement('p'),b=o.bounds_inclusive;
    name.textContent=`${o.name} · ${roles[o.role]}`;
    body.textContent=`初始 x=${b.x_min}–${b.x_max}, y=${b.y_min}–${b.y_max}\n颜色 index: ${o.color_indices.join(', ')} · ${o.cell_count} 格\n${statuses[o.status]}：${o.evidence}`;
    entry.append(name,body);$('ls20-objects').append(entry);
  }
}
function pointerCoordinates(event) {
  const rect=canvas.getBoundingClientRect();
  if(!rect.width || !rect.height) return null;
  const x=Math.max(0,Math.min(canvas.width-1,Math.floor((event.clientX-rect.left)*canvas.width/rect.width)));
  const y=Math.max(0,Math.min(canvas.height-1,Math.floor((event.clientY-rect.top)*canvas.height/rect.height)));
  return {x,y,rect};
}
function hideCoordinates() {
  $('hover-coordinates').hidden=true;$('hover-cell').hidden=true;
  $('coordinates').textContent=`${canvas.width} × ${canvas.height}`;
}
function clearRegion(){
  regionCorners=[];regionSequence=null;regionSession=null;$('selected-region').hidden=true;
  $('selection-info').textContent='启用框选后，依次点击区域的两个角。';
  renderControls();
}
function renderRegion(){
  if(!regionCorners.length)return;
  const a=regionCorners[0],b=regionCorners[1]||a;
  const x0=Math.min(a.x,b.x),x1=Math.max(a.x,b.x),y0=Math.min(a.y,b.y),y1=Math.max(a.y,b.y);
  const rect=canvas.getBoundingClientRect(),stage=$('canvas-stage').getBoundingClientRect(),overlay=$('selected-region');
  overlay.style.left=`${rect.left-stage.left+x0*rect.width/canvas.width}px`;
  overlay.style.top=`${rect.top-stage.top+y0*rect.height/canvas.height}px`;
  overlay.style.width=`${(x1-x0+1)*rect.width/canvas.width}px`;overlay.style.height=`${(y1-y0+1)*rect.height/canvas.height}px`;overlay.hidden=false;
  $('selection-info').textContent=regionCorners.length===1?`第一个角 (${a.x}, ${a.y})；再点击相对的角。`:`x ${x0}–${x1} · y ${y0}–${y1} · ${(x1-x0+1)*(y1-y0+1)} 格（含边界）`;
  renderControls();
}
$('annotation-mode').addEventListener('change',()=>{clearRegion();renderControls();toast($('annotation-mode').checked?'框选模式：点击不会执行游戏动作':'已恢复游戏操作模式');});
$('clear-region').addEventListener('click',clearRegion);
window.addEventListener('resize',()=>{hideCoordinates();renderRegion();});
$('save-region').addEventListener('click',async()=>{
  if(!session||busy||animating||regionCorners.length!==2)return;
  const name=$('object-name').value.trim();if(!name){toast('请先填写物体名称');return;}
  busy=true;renderControls();message('');
  try{
    session=await api(`/api/sessions/${session.session_id}/annotation`,{name,corners:regionCorners,expected_sequence:regionSequence});
    clearRegion();$('object-name').value='';renderSession();toast('区域与矩阵索引已保存到日志');
  }catch(error){message(error.message);}finally{busy=false;renderControls();}
});
canvas.addEventListener('pointermove',event=>{
  if(!session || event.pointerType==='touch') return;
  const pos=pointerCoordinates(event);if(!pos)return;
  const {x,y,rect}=pos,stage=$('canvas-stage').getBoundingClientRect();
  const tip=$('hover-coordinates'),cell=$('hover-cell');
  $('coordinates').textContent=`x ${String(x).padStart(2,'0')}  ·  y ${String(y).padStart(2,'0')}`;
  const value=displayedFrame?.[y]?.[x],index=y*canvas.width+x;
  const detail=`(x, y) = (${x}, ${y})\nmatrix[${y}][${x}] = ${value ?? '—'}\nindex = ${index} · color = ${value ?? '—'}`;
  tip.textContent=detail;$('cell-inspector').textContent=detail;
  tip.style.left=`${Math.max(8,Math.min(event.clientX-stage.left+16,stage.width-235))}px`;
  tip.style.top=`${Math.max(8,Math.min(event.clientY-stage.top+16,stage.height-75))}px`;
  cell.style.left=`${rect.left-stage.left+x*rect.width/canvas.width}px`;
  cell.style.top=`${rect.top-stage.top+y*rect.height/canvas.height}px`;
  cell.style.width=`${rect.width/canvas.width}px`;cell.style.height=`${rect.height/canvas.height}px`;
  tip.hidden=false;cell.hidden=false;
});
canvas.addEventListener('pointerleave',hideCoordinates);
canvas.addEventListener('pointerdown',event=>{
  if(event.button!==0 || !session || busy || animating || session.uncertain) return;
  event.preventDefault();const pos=pointerCoordinates(event);
  if(pos && $('annotation-mode').checked){
    if(regionCorners.length===2)clearRegion();
    regionSequence=session.sequence;regionSession=session.session_id;regionCorners.push({x:pos.x,y:pos.y});renderRegion();return;
  }
  if(!session.observation.available_actions.includes(6))return;
  if(pos)void action(6,{x:pos.x,y:pos.y});
});
document.addEventListener('keydown',event=>{
  if(event.ctrlKey||event.metaKey||event.altKey || ['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName) || event.target.isContentEditable) return;
  const bindings={ArrowUp:1,ArrowDown:2,ArrowLeft:3,ArrowRight:4,w:1,W:1,s:2,S:2,a:3,A:3,d:4,D:4,' ':5,z:7,Z:7,r:0,R:0};
  const id=bindings[event.key];if(id===undefined || !session)return;
  event.preventDefault();if(event.repeat && (id===0 || id===7))return;
  const button=document.querySelector(`[data-action="${id}"]`);if(button && !button.disabled)void action(id);
});
$('save-note').addEventListener('click',async()=>{
  if(!session||busy)return;
  const text=$('note').value.trim();if(!text){toast('先写下一点观察吧');return;}
  busy=true;renderControls();
  try {session=await api(`/api/sessions/${session.session_id}/note`,{text});$('note').value='';$('note-status').textContent=`已保存 ${session.notes.length} 条笔记`;toast('笔记已写入日志');}
  catch(error){message(error.message);}finally{busy=false;renderControls();}
});
$('finish').addEventListener('click',async()=>{
  if(!session||busy)return;
  if(!confirm('结束本轮并下载？结束后不可继续操作，但日志会保留。'))return;
  busy=true;renderControls();
  try {session=await api(`/api/sessions/${session.session_id}/end`,{});renderSession();download(true);await recent();}
  catch(error){message(error.message);}finally{busy=false;renderControls();}
});
setInterval(()=>{const end=session?.ended_at?Date.parse(session.ended_at):Date.now();const seconds=started?Math.max(0,Math.floor((end-started)/1000)):0;$('elapsed').textContent=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;},1000);
async function init(){
  try{const data=await api('/api/games');games=data.games;palette=data.palette;renderSession();await recent();const id=localStorage.getItem('arc-human-session');if(id)await restore(id);}
  catch(error){message(error.message);}
}
void init();

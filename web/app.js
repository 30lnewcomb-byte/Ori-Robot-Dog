const state={mode:'SAFE',battery:82,sequence:0,joints:Array.from({length:16},(_,i)=>({id:i+1,pos:0}))};
const $=id=>document.getElementById(id);
function log(message){const row=document.createElement('div');row.className='log-line';row.textContent=`[${new Date().toLocaleTimeString()}] ${message}`;$('log').prepend(row)}
function render(){
  $('systemStatus').textContent=state.mode;$('mode').textContent=state.mode;$('batteryFill').style.width=`${state.battery}%`;$('batteryText').textContent=`${state.battery}%`;
  $('joints').innerHTML=state.joints.map(j=>`<div class="joint"><span>J${String(j.id).padStart(2,'0')}</span><b>${j.pos.toFixed(1)}°</b></div>`).join('');
}
function setMode(mode){state.mode=mode;state.sequence++;log(`Mode changed to ${mode} (simulation)`);if(mode==='STAND') state.joints.forEach(j=>j.pos=(Math.random()*8-4));if(mode==='SAFE') state.joints.forEach(j=>j.pos=0);render()}
$('standBtn').addEventListener('click',()=>setMode('STAND'));
$('sitBtn').addEventListener('click',()=>setMode('SIT'));
$('safeBtn').addEventListener('click',()=>setMode('SAFE'));
$('clearLog').addEventListener('click',()=>{$('log').innerHTML=''});
setInterval(()=>{if(state.mode!=='SAFE'){state.joints.forEach(j=>j.pos+=(Math.random()-.5)*.8);state.battery=Math.max(0,state.battery-.02);render()}},500);
log('Browser control center started');log('Simulation mode enabled; no hardware commands available');render();

const state={mode:'SAFE',battery:null,connected:false,telemetry:false,sequence:0,joints:Array.from({length:16},(_,i)=>({id:i+1,pos:0}))};
const $=id=>document.getElementById(id);
const config={apiBase:localStorage.getItem('oriApiBase')||'http://ori.local:8000'};
function log(message){const row=document.createElement('div');row.className='log-line';row.textContent=`[${new Date().toLocaleTimeString()}] ${message}`;$('log').prepend(row)}
function render(){
  $('systemStatus').textContent=state.mode;$('mode').textContent=state.mode;$('piStatus').textContent=state.connected?'Connected':'Disconnected';$('telemetry').textContent=state.telemetry?'Live':'Waiting';
  $('connectionText').textContent=state.connected?'PI CONNECTED':'OFFLINE';$('controlMode').textContent=state.connected?'LIVE API':'SIMULATION';
  $('batteryFill').style.width=state.battery==null?'0':`${state.battery}%`;$('batteryText').textContent=state.battery==null?'--':`${state.battery}%`;
  $('joints').innerHTML=state.joints.map(j=>`<div class="joint"><span>J${String(j.id).padStart(2,'0')}</span><b>${Number(j.pos).toFixed(1)}°</b></div>`).join('');
}
function applyTelemetry(data){
  if(typeof data.battery_percent==='number') state.battery=data.battery_percent;
  if(data.mode) state.mode=String(data.mode).toUpperCase();
  if(Array.isArray(data.joints)) data.joints.forEach((j,i)=>{if(state.joints[i]&&typeof j.position_deg==='number')state.joints[i].pos=j.position_deg});
  if(data.imu) $('imu').textContent=data.imu.status||'Stable';
  if(Array.isArray(data.feet)) $('feet').textContent=`${data.feet.filter(Boolean).length} / ${data.feet.length}`;
  state.telemetry=true;render();
}
async function connect(){
  config.apiBase=$('apiBase').value.trim().replace(/\/$/,'');localStorage.setItem('oriApiBase',config.apiBase);OriAPI.configure(config.apiBase);
  try{const status=await OriAPI.connect();state.connected=true;applyTelemetry(status);log(`Connected to Pi API at ${config.apiBase}`);OriAPI.connectTelemetry(applyTelemetry,connected=>{state.telemetry=connected;if(!connected)log('Telemetry stream disconnected');render()});startCamera();}
  catch(error){state.connected=false;state.telemetry=false;log(`Pi connection failed: ${error.message}`);render();}
}
async function command(type,payload={}){
  state.sequence++;
  if(!state.connected){log(`${type}: simulation only — Pi is not connected`);if(type==='stand')state.mode='STAND';if(type==='sit')state.mode='SIT';if(type==='safe')state.mode='SAFE';render();return;}
  try{await OriAPI.command(type,payload);log(`Command sent: ${type}`)}catch(error){log(`Command failed: ${error.message}`)}
}
async function safe(){state.mode='SAFE';render();if(state.connected){try{await OriAPI.safe();log('SAFE command sent to Pi')}catch(error){log(`SAFE command failed: ${error.message}`)}}else log('SAFE selected locally; Pi is disconnected')}
function bindDrive(){document.querySelectorAll('[data-drive]').forEach(button=>{const action=button.dataset.drive;const send=()=>command('drive',{direction:action,speed:action==='stop'?0:0.35});button.addEventListener('pointerdown',send);button.addEventListener('pointerup',()=>command('drive',{direction:'stop',speed:0}));button.addEventListener('pointercancel',()=>command('drive',{direction:'stop',speed:0}));});window.addEventListener('keydown',e=>{const map={ArrowUp:'forward',ArrowDown:'backward',ArrowLeft:'left',ArrowRight:'right'};if(map[e.key]&&!e.repeat){e.preventDefault();command('drive',{direction:map[e.key],speed:0.35})}});window.addEventListener('keyup',e=>{if(e.key.startsWith('Arrow'))command('drive',{direction:'stop',speed:0})})}
async function startCamera(){
  $('cameraPlaceholder').classList.remove('hidden');$('videoStatus').textContent='CONNECTING';
  try{const offer=await OriAPI.cameraOffer();if(!offer?.sdp)throw new Error('Camera offer unavailable');const pc=new RTCPeerConnection();pc.ontrack=e=>{$('camera').srcObject=e.streams[0];$('cameraPlaceholder').classList.add('hidden');$('videoStatus').textContent='LIVE';$('cameraState').textContent='Live'};await pc.setRemoteDescription(offer);const answer=await pc.createAnswer();await pc.setLocalDescription(answer);await OriAPI.cameraAnswer({sdp:pc.localDescription.sdp,type:pc.localDescription.type});}catch(error){$('videoStatus').textContent='NO SIGNAL';$('cameraState').textContent='Unavailable';log(`Camera stream not connected: ${error.message}`)}
}
$('apiBase').value=config.apiBase;$('connectBtn').addEventListener('click',connect);$('standBtn').addEventListener('click',()=>command('stand'));$('sitBtn').addEventListener('click',()=>command('sit'));$('safeBtn').addEventListener('click',safe);$('clearLog').addEventListener('click',()=>{$('log').innerHTML=''});bindDrive();log('Ori Pilot started');log('Live-camera API architecture loaded');render();

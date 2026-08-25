const state={safe:true,battery:null,connected:false,telemetry:false,auto:false,activeInput:null,joints:Array.from({length:16},(_,i)=>({id:i+1,pos:0}))};
const $=id=>document.getElementById(id);
const config={apiBase:localStorage.getItem('oriApiBase')||'http://ori.local:8000'};
let heartbeatTimer=null;
let recognition=null;
function log(message){const row=document.createElement('div');row.className='log-line';row.textContent=`[${new Date().toLocaleTimeString()}] ${message}`;$('log').prepend(row)}
function render(){
  $('systemStatus').textContent=state.safe?'SAFE':'READY';
  $('safetyState').textContent=state.safe?'SAFE':'RELEASED';
  $('piStatus').textContent=state.connected?'Connected':'Disconnected';
  $('telemetry').textContent=state.telemetry?'Live':'Waiting';
  $('connectionText').textContent=state.connected?'PI CONNECTED':'OFFLINE';
  $('controlSource').textContent=state.activeInput?`${state.activeInput.toUpperCase()} INPUT`:'NO ACTIVE INPUT';
  $('activeInput').textContent=state.activeInput||'None';
  $('browserPresent').textContent=state.connected?'Yes':'No';
  $('autoState').textContent=state.auto?'Running':'Ready';
  $('autoPlanning').textContent=state.auto?'Planning':'Idle';
  $('autoBtn').textContent=state.auto?'Stop auto-pilot':'Auto-pilot';
  $('batteryFill').style.width=state.battery==null?'0':`${state.battery}%`;
  $('batteryText').textContent=state.battery==null?'--':`${state.battery}%`;
  $('joints').innerHTML=state.joints.map(j=>`<div class="joint"><span>J${String(j.id).padStart(2,'0')}</span><b>${Number(j.pos).toFixed(1)}°</b></div>`).join('');
}
function applyTelemetry(data){
  if(typeof data.battery_percent==='number') state.battery=data.battery_percent;
  state.safe=Boolean(data.safe);
  state.auto=Boolean(data.auto_pilot?.running);
  state.activeInput=data.selected_source||null;
  if(Array.isArray(data.joints)) data.joints.forEach((j,i)=>{if(state.joints[i]&&typeof j.position_deg==='number')state.joints[i].pos=j.position_deg});
  if(data.imu) $('imu').textContent=data.imu.status||'Stable';
  if(Array.isArray(data.feet)) $('feet').textContent=`${data.feet.filter(Boolean).length} / ${data.feet.length}`;
  state.telemetry=true;render();
}
async function connect(){
  config.apiBase=$('apiBase').value.trim().replace(/\/$/,'');localStorage.setItem('oriApiBase',config.apiBase);OriAPI.configure(config.apiBase);
  try{const status=await OriAPI.connect();state.connected=true;applyTelemetry(status);log(`Connected to Pi API at ${config.apiBase}`);OriAPI.connectTelemetry(applyTelemetry,connected=>{state.telemetry=connected;if(!connected)log('Telemetry stream disconnected');render()});startCamera();startHeartbeat();}
  catch(error){state.connected=false;state.telemetry=false;log(`Pi connection failed: ${error.message}`);render();}
}
function startHeartbeat(){if(heartbeatTimer)clearInterval(heartbeatTimer);heartbeatTimer=setInterval(()=>{if(state.connected)OriAPI.heartbeat('browser').catch(()=>{});},500);OriAPI.heartbeat('browser').catch(()=>{});}
async function command(type,payload={}){
  if(!state.connected){log(`${type}: Pi is not connected`);return;}
  try{const result=await OriAPI.command(type,{...payload,source:'browser'});state.activeInput=result.selected_source||'browser';log(`Browser intent sent: ${type}`);render();}catch(error){log(`Command failed: ${error.message}`)}
}
async function safe(){try{await OriAPI.safe();state.safe=true;state.activeInput=null;log('SAFE command sent to Pi');render()}catch(error){log(`SAFE command failed: ${error.message}`)}}
async function releaseSafety(){try{await OriAPI.releaseSafety();state.safe=false;log('Safety released by explicit browser action');render()}catch(error){log(`Safety release failed: ${error.message}`)}}
async function toggleAuto(){if(state.auto){await command('auto_stop')}else{try{await OriAPI.releaseSafety();state.safe=false;await OriAPI.command('auto_start',{source:'auto'});log('Auto-pilot started; browser remains available as a higher-priority input');}catch(error){log(`Auto-pilot failed: ${error.message}`)}}}
function bindDrive(){document.querySelectorAll('[data-drive]').forEach(button=>{const action=button.dataset.drive;button.addEventListener('pointerdown',()=>command('drive',{direction:action,speed:action==='stop'?0:0.35}));button.addEventListener('pointerup',()=>command('drive',{direction:'stop',speed:0}));button.addEventListener('pointercancel',()=>command('drive',{direction:'stop',speed:0}));});window.addEventListener('keydown',e=>{const map={ArrowUp:'forward',ArrowDown:'backward',ArrowLeft:'left',ArrowRight:'right'};if(map[e.key]&&!e.repeat){e.preventDefault();command('drive',{direction:map[e.key],speed:0.35})}});window.addEventListener('keyup',e=>{if(e.key.startsWith('Arrow'))command('drive',{direction:'stop',speed:0})})}
function setupVoice(){const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){$('voiceStatus').textContent='Browser speech recognition is unavailable; use Pi-side voice input later.';return}recognition=new SpeechRecognition();recognition.lang='en-US';recognition.interimResults=false;recognition.continuous=false;recognition.onstart=()=>{$('voiceStatus').textContent='Listening…';};recognition.onend=()=>{$('voiceStatus').textContent='Voice ready.';};recognition.onerror=e=>{$('voiceStatus').textContent=`Voice error: ${e.error}`;};recognition.onresult=async e=>{const text=e.results[0][0].transcript;log(`Voice heard: “${text}”`);try{const result=await OriAPI.voice(text);if(result.accepted){state.activeInput='voice';log(`Voice intent: ${result.intent}`)}else log('Voice phrase not understood by Pi parser');}catch(error){log(`Voice request failed: ${error.message}`)}render()};$('voiceBtn').addEventListener('click',()=>{try{recognition.start()}catch(_){}})}
async function startCamera(){
  $('cameraPlaceholder').classList.remove('hidden');$('videoStatus').textContent='CONNECTING';
  try{const offer=await OriAPI.cameraOffer();if(!offer?.sdp)throw new Error('Camera offer unavailable');const pc=new RTCPeerConnection();pc.ontrack=e=>{$('camera').srcObject=e.streams[0];$('cameraPlaceholder').classList.add('hidden');$('videoStatus').textContent='LIVE';$('cameraState').textContent='Live'};await pc.setRemoteDescription(offer);const answer=await pc.createAnswer();await pc.setLocalDescription(answer);await OriAPI.cameraAnswer({sdp:pc.localDescription.sdp,type:pc.localDescription.type});}catch(error){$('videoStatus').textContent='NO SIGNAL';$('cameraState').textContent='Unavailable';log(`Camera stream not connected: ${error.message}`)}
}
$('apiBase').value=config.apiBase;$('connectBtn').addEventListener('click',connect);$('standBtn').addEventListener('click',async()=>{if(state.safe)await releaseSafety();command('stand')});$('sitBtn').addEventListener('click',()=>command('sit'));$('autoBtn').addEventListener('click',toggleAuto);$('safeBtn').addEventListener('click',safe);$('clearLog').addEventListener('click',()=>{$('log').innerHTML=''});bindDrive();setupVoice();log('Ori Pilot started');log('Auto-pilot, browser, and voice are concurrent input sources');render();

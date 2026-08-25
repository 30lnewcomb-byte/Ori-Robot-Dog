const OriAPI = (() => {
  let baseUrl = '';
  let socket = null;

  function configure(url) { baseUrl = url.replace(/\/$/, ''); }

  async function request(path, options = {}) {
    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.status === 204 ? null : response.json();
  }

  function connectTelemetry(onMessage, onState) {
    if (socket) socket.close();
    const wsUrl = baseUrl.replace(/^http/, 'ws') + '/api/v1/telemetry';
    socket = new WebSocket(wsUrl);
    socket.onopen = () => onState(true);
    socket.onclose = () => onState(false);
    socket.onerror = () => onState(false);
    socket.onmessage = event => { try { onMessage(JSON.parse(event.data)); } catch (_) {} };
    return socket;
  }

  return {
    configure,
    connect: () => request('/api/v1/status'),
    command: (type, payload = {}) => request('/api/v1/command', {
      method: 'POST', body: JSON.stringify({ type, payload, timestamp: Date.now() })
    }),
    safe: () => request('/api/v1/safe', { method: 'POST', body: '{}' }),
    releaseSafety: () => request('/api/v1/safety/release', { method: 'POST', body: '{}' }),
    heartbeat: (source = 'browser') => request('/api/v1/source/heartbeat', {
      method: 'POST', body: JSON.stringify({ source, ttl_s: 1.5 })
    }),
    voice: (text) => request('/api/v1/voice', {
      method: 'POST', body: JSON.stringify({ text })
    }),
    cameraOffer: () => request('/api/v1/camera/offer'),
    cameraAnswer: (answer) => request('/api/v1/camera/answer', {
      method: 'POST', body: JSON.stringify(answer)
    }),
    connectTelemetry
  };
})();

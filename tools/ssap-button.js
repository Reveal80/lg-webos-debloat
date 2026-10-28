// ssap-button.js: runs ON the TV with the TV's own node. Presses one remote button through LG's SSAP API
// (wss://127.0.0.1:3001 → getPointerInputSocket), since webOS does not take arrow keys over luna-send.
// Started by tools/lgtv.py; you do not run it yourself.
//
//   node ssap-button.js <client-key|-> <BUTTON>    UP DOWN LEFT RIGHT ENTER BACK MENU EXIT INFO HOME ...
//   node ssap-button.js --pair                     ask the TV for a client key (accept the prompt on screen)
const WS = require('/usr/palm/services/com.webos.service.secondscreen.gateway/node_modules/ws');
const pair = process.argv[2] === '--pair';
const key = pair || process.argv[2] === '-' ? '' : process.argv[2];
const name = process.argv[3];
const manifest = { appVersion: '1.1', manifestVersion: 1, permissions: ['CONTROL_INPUT_JOYSTICK',
  'CONTROL_INPUT_MEDIA_PLAYBACK', 'CONTROL_INPUT_TV', 'CONTROL_MOUSE_AND_KEYBOARD', 'READ_INPUT_DEVICE_LIST'] };
const ws = new WS('wss://127.0.0.1:3001', { rejectUnauthorized: false });
const bye = setTimeout(() => { console.log(pair ? 'TIMEOUT: nobody accepted the prompt on the TV' : 'TIMEOUT'); process.exit(2); }, pair ? 60000 : 8000);
ws.onopen = () => ws.send(JSON.stringify({ type: 'register', id: 'reg', payload: Object.assign(
  { forcePairing: false, pairingType: 'PROMPT', manifest }, key ? { 'client-key': key } : {}) }));
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.type === 'registered') {
    if (pair) { console.log('CLIENT-KEY ' + m.payload['client-key']); clearTimeout(bye); process.exit(0); }
    ws.send(JSON.stringify({ type: 'request', id: 'r1', uri: 'ssap://com.webos.service.networkinput/getPointerInputSocket' }));
    return;
  }
  if (m.type === 'error') { console.log('ERROR ' + (m.error || '')); process.exit(1); }
  if (m.id === 'r1') {
    const sp = m.payload && m.payload.socketPath;
    if (!sp) { console.log('ERROR no pointer socket (pair first: lgtv.py <ip> pair)'); process.exit(1); }
    const p = new WS(sp, { rejectUnauthorized: false });
    p.onopen = () => { p.send('type:button\nname:' + name + '\n\n'); setTimeout(() => { clearTimeout(bye); process.exit(0); }, 250); };
    p.onerror = () => process.exit(1);
  }
};
ws.onerror = () => { console.log('ERROR cannot reach SSAP on the TV'); process.exit(1); };

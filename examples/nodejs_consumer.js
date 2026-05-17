/**
 * VUT Headless SDK — Node.js Consumer
 * Connects to tracker daemon and prints live poses.
 * Run: node nodejs_consumer.js
 * Requires: npm install ws
 */
const WebSocket = require('ws');

const WS_URL = 'ws://localhost:8765';

const ws = new WebSocket(WS_URL);

ws.on('open', () => {
  console.log(`Connected to ${WS_URL}`);
});

ws.on('message', (data) => {
  const poses = JSON.parse(data);
  Object.entries(poses).forEach(([serial, pose]) => {
    if (serial === 'meta') return;
    const { x, y, z } = pose.position;
    console.log(
      `${serial} [${pose.status}] ` +
      `x=${x.toFixed(3)} y=${y.toFixed(3)} z=${z.toFixed(3)} ` +
      `battery=${pose.battery_pct}%`
    );
  });
});

ws.on('error', (err) => {
  console.error('WebSocket error:', err.message);
  console.error('Is START_VUT_ROBOTICS_SDK.bat running?');
});

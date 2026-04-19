const express = require('express');
const cors = require('cors');
const path = require('path');
const app = express();
const PORT = process.env.HERMES_PORT||3001;

app.use(cors({origin:true,methods:['GET','POST','OPTIONS'],allowedHeaders:['Content-Type','Authorization']}));
app.use((req,res,next)=>{res.setHeader('Access-Control-Allow-Origin','*');if(req.method==='OPTIONS')return res.status(204).end();next();});
app.use(express.json());

const projectRoot=path.join(__dirname,'..');
app.use('/audio_output',express.static(path.join(projectRoot,'audio_output')));

app.use('/api/hermes',require('./routes/prompt'));
app.use('/api/hermes',require('./routes/chat'));
app.use('/api/hermes',require('./routes/route'));
app.use('/api/hermes/music',require('./routes/music'));

// Telegram Bridge API
const { sendToTelegram, getNewMessages, getConnectionStatus } = require('./routes/telegram-bridge');
app.get('/api/hermes/bridge/status', (req,res) => res.json({ success:true, ...getConnectionStatus() }));
app.get('/api/hermes/bridge/messages', (req,res) => {
  const since = parseInt(req.query.since) || 0;
  res.json({ success:true, messages: getNewMessages(since) });
});
app.post('/api/hermes/bridge/send', async (req,res) => {
  const { text } = req.body;
  if (!text) return res.status(400).json({ success:false, error:'請提供 text' });
  const result = await sendToTelegram(text);
  res.json({ success: result.ok !== false, ...result });
});

app.get('/api/hermes/health',(req,res)=>res.json({status:'ok',service:'hermes-api-server',version:'1.0.0',timestamp:new Date().toISOString(),uptime:process.uptime()}));

app.get('/api/hermes',(req,res)=>res.json({name:'Hermes API Server',version:'1.0.0',endpoints:[
  {method:'POST',path:'/api/hermes/enhance',desc:'智慧提示詞增強'},
  {method:'POST',path:'/api/hermes/chat',desc:'對話式 AI 助手'},
  {method:'POST',path:'/api/hermes/route',desc:'智慧引擎路由'},
  {method:'POST',path:'/api/hermes/music/generate',desc:'音樂生成'},
  {method:'GET',path:'/api/hermes/engines',desc:'引擎列表'},
  {method:'GET',path:'/api/hermes/music/styles',desc:'音樂風格'},
  {method:'GET',path:'/api/hermes/health',desc:'健康檢查'},
]}));

// Telegram Bot
const { getBot: startTelegramBot } = require('./routes/telegram');

app.use((req,res)=>res.status(404).json({success:false,error:'Not found'}));

app.listen(PORT,()=>{
  console.log(`\n🐯 Hermes API Server v1.0.0 | Port ${PORT}\n   Health: /api/hermes/health\n   Docs:   /api/hermes\n`);
  // Start Telegram bot (skip if DISABLE_TELEGRAM is set to avoid conflict with Hermes Agent)
  if (!process.env.DISABLE_TELEGRAM) {
    startTelegramBot();
  }
});
module.exports=app;

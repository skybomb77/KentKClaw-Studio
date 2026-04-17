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

app.use((req,res)=>res.status(404).json({success:false,error:'Not found'}));

app.listen(PORT,()=>console.log(`\n🐯 Hermes API Server v1.0.0 | Port ${PORT}\n   Health: /api/hermes/health\n   Docs:   /api/hermes\n`));
module.exports=app;

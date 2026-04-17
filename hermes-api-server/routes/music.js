const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const TONEFORGE_API = process.env.TONEFORGE_API||'http://127.0.0.1:8787';
const pythonPath = process.env.PYTHON_PATH||path.join(__dirname,'..','..','.venv','bin','python');

router.post('/generate', async (req,res) => {
  const {style,mood,duration}=req.body;
  const s=style||'Lofi Hip Hop', m=mood||'chill vibes', d=duration||15;
  console.log(`[Hermes Music] ${s} | ${m} | ${d}s`);
  try {
    const payload=JSON.stringify({prompt:`${s}, ${m}`,useCase:'background-music',duration:`${d}s`});
    const url=new URL(TONEFORGE_API+'/generate');
    const proxyReq=http.request({hostname:url.hostname,port:url.port,path:url.pathname,method:'POST',headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(payload)}},(proxyRes)=>{
      let data='';proxyRes.on('data',c=>data+=c);proxyRes.on('end',()=>{try{res.json({success:true,source:'toneforge-api',...JSON.parse(data)})}catch(e){res.json({success:true,source:'toneforge-api',raw:data})}});
    });
    proxyReq.on('error',()=>generateLocal(s,m,d,res));
    proxyReq.write(payload);proxyReq.end();
  } catch(e) { generateLocal(s,m,d,res); }
});

function generateLocal(style,mood,duration,res) {
  const outputDir=path.join(__dirname,'..','..','audio_output');
  if(!fs.existsSync(outputDir))fs.mkdirSync(outputDir,{recursive:true});
  const outputFile=path.join(outputDir,`hermes_${Date.now()}.wav`);
  const scriptPath=path.join(__dirname,'..','..','scripts','generate_music.py');
  if(!fs.existsSync(scriptPath))return res.status(500).json({success:false,error:'腳本不存在'});
  console.log(`[Hermes Music] Local DSP: ${style}`);
  const proc=spawn(pythonPath,[scriptPath,'--style',style,'--duration',String(duration),'--output',outputFile]);
  let err='';proc.stderr.on('data',d=>err+=d.toString());
  proc.on('close',code=>{
    if(code===0&&fs.existsSync(outputFile)){
      const fn=path.basename(outputFile);
      res.json({success:true,source:'local-dsp',style,mood,duration,filename:fn,audioUrl:`/audio_output/${fn}`,message:'音樂生成完成！'});
    } else res.status(500).json({success:false,error:`生成失敗 (code:${code})`,details:err});
  });
  proc.on('error',e=>res.status(500).json({success:false,error:e.message}));
}

router.get('/styles',(req,res)=>res.json({success:true,styles:[
  {name:'Lofi Hip Hop',bpm:'72-88',mood:'放鬆'},{name:'Techno',bpm:'124-138',mood:'派對'},
  {name:'Cyberpunk',bpm:'124-138',mood:'賽博'},{name:'Cinematic',bpm:'55-75',mood:'史詩'},
  {name:'Epic',bpm:'55-75',mood:'宏大'},{name:'Acoustic',bpm:'95-115',mood:'溫暖'}
]}));
module.exports=router;

const express = require('express');
const router = express.Router();
const { enhance, ENGINE_PROFILES } = require('../utils/prompt-engine');
router.post('/route', (req,res) => {
  const {input,preferEngine} = req.body;
  if (!input) return res.status(400).json({success:false,error:'請提供 input'});
  try {
    const a = enhance(input);
    if (preferEngine && ENGINE_PROFILES[preferEngine]) a.recommendation.engine = preferEngine;
    res.json({success:true, analysis:a, apiCall:{engine:a.recommendation.engine,endpoint:a.recommendation.apiEndpoint,method:a.recommendation.method,body:a.recommendation.body||a.recommendation}, allEngines:ENGINE_PROFILES});
  } catch(e) { res.status(500).json({success:false,error:e.message}); }
});
router.get('/recommend/:keyword', (req,res) => {
  const m={music:'toneforge',音樂:'toneforge',video:'wirevision',影片:'wirevision',animation:'frameforge',動畫:'frameforge',photo:'snapforge',商品:'snapforge',comic:'comicforge',漫畫:'comicforge'};
  const k=m[req.params.keyword.toLowerCase()];
  res.json(k&&ENGINE_PROFILES[k]?{success:true,keyword:req.params.keyword,engine:k,profile:ENGINE_PROFILES[k]}:{success:false,keyword:req.params.keyword,message:'找不到引擎',available:Object.keys(m)});
});
module.exports = router;

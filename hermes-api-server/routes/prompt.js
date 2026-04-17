const express = require('express');
const router = express.Router();
const { enhance } = require('../utils/prompt-engine');
router.post('/enhance', (req,res) => {
  const {input} = req.body;
  if (!input) return res.status(400).json({success:false,error:'請提供 input'});
  try { res.json({success:true, ...enhance(input)}); } catch(e) { res.status(500).json({success:false,error:e.message}); }
});
router.get('/engines', (req,res) => { const {ENGINE_PROFILES}=require('../utils/prompt-engine'); res.json({success:true,engines:ENGINE_PROFILES,count:Object.keys(ENGINE_PROFILES).length}); });
module.exports = router;

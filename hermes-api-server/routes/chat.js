const express = require('express');
const router = express.Router();
const { chat } = require('../utils/chat-engine');
router.post('/chat', (req,res) => {
  const {message,context} = req.body;
  if (!message) return res.status(400).json({success:false,error:'請提供 message'});
  try { res.json({success:true, ...chat(message,context||{})}); } catch(e) { res.status(500).json({success:false,error:e.message}); }
});
module.exports = router;

# Kent & KClaw Studio — QA 測試報告

**日期：** 2026-04-19  
**測試員：** KClaw (自動化 QA)  
**測試範圍：** 主登陸頁 + APP 登入頁

---

## 總結

| 類別 | 數量 |
|------|------|
| 測試頁面 | 2 個 |
| 發現問題 | 5 個 |
| Critical | 0 |
| High | 2 |
| Medium | 2 |
| Low | 1 |

---

## 問題列表

### BUG-01: Clerk 顯示「Development mode」[HIGH]
**頁面：** app/index.html（登入 & 註冊頁）  
**類別：** Content / UX  
**描述：** Clerk 登入視窗底部顯示 "Development mode" 字樣，用戶會以為這是測試環境  
**重現：** 瀏覽 app/index.html → 看到登入視窗底部  
**預期：** 不應該顯示此標籤，或改為更友好的提示  
**修復建議：** 在 Clerk Dashboard 中將應用從 Development 改為 Production 模式

### BUG-02: Pricing CTA 連結導向外部站 [HIGH]  
**頁面：** index.html（定價區塊）  
**類別：** Functional  
**描述：** Free 和 Pro 的 CTA 按鈕連結到 `toneforge-site/app.html` 而非本站 app  
**重現：** 滾到 Pricing → 點 "Get Started Free" 或 "Start Pro Trial"  
**預期：** 應該導向 `app/index.html` 或本站的註冊頁  
**影響：** 用戶被導到其他站，可能困惑

### BUG-03: ComicForge 外部連結 [MEDIUM]  
**頁面：** index.html  
**類別：** Consistency  
**描述：** 其他 4 個引擎都連結本站頁面，唯獨 ComicForge 連結到 `comicforge-site` 外部站  
**重現：** 導航列點 ComicForge 漫鍛  
**預期：** 應保持一致性 — 要嘛都內部，要嘛在新分頁開啟  
**影響：** 用戶體驗不一致

### BUG-04: 首頁文字殘留 code fence [MEDIUM]  
**頁面：** index.html  
**類別：** Content  
**描述：** 頁面 snapshot 顯示開頭有 `` ```javascript `` 的 code fence 文字殘留  
**重現：** 瀏覽 index.html → DOM 開頭有 code fence 文字  
**預期：** 不應該有此殘留文字  
**影響：** 視覺上可能不明顯，但 DOM 結構不乾淨

### BUG-05: Sign Up 連結可能損壞 [LOW]  
**頁面：** app/index.html（登入頁）  
**類別：** Functional  
**描述：** Sign Up 連結 URL 包含 `__clerk_db_jwt` 參數，此 token 可能過期  
**重現：** 登入頁 → 點 "Sign up"  
**預期：** 連結應動態生成，不依賴過期 token  
**影響：** 低 — Clerk 通常會重新導向

---

## 測試通過項目 ✅

### 主登陸頁 (index.html)
- ✅ 導航列完整（5 引擎 + GitHub + i18n + Sign In）
- ✅ Hero 區塊清晰
- ✅ 三步驟流程設計好
- ✅ 產品篩選按鈕（全部/音樂/影片/圖片/商業/創作）
- ✅ 團隊介紹（Kent, KClaw, KTlaw）
- ✅ 用戶見證 3 則
- ✅ 定價方案（Free/Pro/Enterprise）
- ✅ FAQ 區塊完整
- ✅ Footer 有 Terms/Privacy/Email
- ✅ 無 JS Console 錯誤

### APP 登入頁 (app/index.html)
- ✅ Clerk OAuth 按鈕完整（Apple/Facebook/Google/X）
- ✅ Email + Password 表單
- ✅ Show/Hide 密碼切換正常
- ✅ 錯誤處理：「Couldn't find your account.」
- ✅ Console 422 錯誤（預期的 API 錯誤）
- ✅ Sign Up 頁結構完整
- ✅ Terms of Service 和 Privacy Policy 連結存在
- ✅ 側邊欄導航結構完整

---

## 測試備註

- Vision API 404 錯誤，截圖無法自動分析，改用 DOM snapshot
- 無法登入測試 APP 內部功能（需有效帳戶）
- 只測了桌面版，未測行動裝置
- 未測 ToneForge/WireVision/FrameForge/SnapForge 個別產品頁

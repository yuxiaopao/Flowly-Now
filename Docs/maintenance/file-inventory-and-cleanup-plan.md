# Flowly-now 椤圭洰鏂囦欢娓呭崟涓庢暣鐞嗗缓璁?
鐢熸垚鏃ユ湡锛?026-06-12

---

## 涓€銆佹枃浠跺垎绫绘€昏

### 1. 鍚庣鏍稿績浠ｇ爜锛圖jango Backend锛?
> 璺緞锛歚Backend/` 鈥?Django 椤圭洰涓讳綋锛屽叡 28 涓簲鐢ㄦā鍧?
| 妯″潡 | 璺緞 | 璇存槑 |
|------|------|------|
| `admin` | `Backend/admin/` | 绠＄悊鍚庡彴鍏ュ彛 |
| `agents` | `Backend/agents/` | AI Agent 绠＄悊锛堝惈 Desktop銆丮ulti-Agent锛?|
| `annotations` | `Backend/annotations/` | 鏁版嵁鏍囨敞妯″潡 |
| `augmentation` | `Backend/augmentation/` | 鏁版嵁澧炲己 |
| `billing` | `Backend/billing/` | 璁¤垂妯″潡 |
| `branding` | `Backend/branding/` | 鍝佺墝瀹氬埗 |
| `codegraph` | `Backend/codegraph/` | 浠ｇ爜鍥捐氨锛圵ebSocket锛?|
| `config` | `Backend/config/` | Django 閰嶇疆锛坰ettings銆乧elery銆乤sgi锛?|
| `core` | `Backend/core/` | 鏍稿績宸ュ叿绫?|
| `dataset_recommend` | `Backend/dataset_recommend/` | 鏁版嵁闆嗘帹鑽?|
| `datasets` | `Backend/datasets/` | 鏁版嵁闆嗙鐞?|
| `evaluation` | `Backend/evaluation/` | 妯″瀷璇勪及 |
| `features` | `Backend/features/` | 鐗规€у紑鍏?|
| `gateway` | `Backend/gateway/` | LLM 缃戝叧鏈嶅姟 |
| `integrations` | `Backend/integrations/` | 涓夋柟闆嗘垚 |
| `marketplace` | `Backend/marketplace/` | 妯℃澘甯傚満 |
| `monitoring` | `Backend/monitoring/` | 鐩戞帶妯″潡 |
| `nl_to_workflow` | `Backend/nl_to_workflow/` | 鑷劧璇█杞伐浣滄祦锛堟牳蹇冿級 |
| `prompts` | `Backend/prompts/` | 鎻愮ず璇嶇鐞?|
| `rag` | `Backend/rag/` | RAG 妫€绱㈠寮?|
| `templates` | `Backend/templates/` | 妯℃澘绠＄悊 |
| `tenants` | `Backend/tenants/` | 澶氱鎴?|
| `training` | `Backend/training/` | 妯″瀷璁粌锛圵ebSocket锛?|
| `users` | `Backend/users/` | 鐢ㄦ埛璁よ瘉 |
| `utils` | `Backend/utils/` | 宸ュ叿鍑芥暟锛堢紦瀛樸€佷腑闂翠欢銆侀獙璇佸櫒锛?|
| `website_generator` | `Backend/website_generator/` | 缃戠珯鐢熸垚鍣?|
| `workflows` | `Backend/workflows/` | 宸ヤ綔娴佸紩鎿庯紙鏍稿績锛?|
| `scripts` | `Backend/scripts/` | 杩愮淮/妫€鏌ヨ剼鏈?|
| `reports` | `Backend/reports/` | API 妫€鏌ユ姤鍛婏紙涓存椂锛?|

**鏍稿績鍏ュ彛鏂囦欢**锛歚Backend/manage.py`銆乣Backend/conftest.py`銆乣Backend/requirements.txt`銆乣Backend/.env.example`

---

### 2. 鍓嶇鏍稿績浠ｇ爜锛圴ue.js Frontend锛?
> 璺緞锛歚Frontend/` 鈥?Vue 3 + Vite + TypeScript

| 绫诲埆 | 璺緞 | 璇存槑 |
|------|------|------|
| 璺敱鍏ュ彛 | `Frontend/src/main.js`銆乣Frontend/src/App.vue` | 搴旂敤鍏ュ彛 |
| 浠〃鐩?| `Frontend/src/views/dashboard/Home.vue` | 棣栭〉 |
| 璁よ瘉 | `Frontend/src/views/auth/` | 鐧诲綍/娉ㄥ唽/鎵惧洖瀵嗙爜锛? 鏂囦欢锛?|
| 宸ヤ綔娴?| `Frontend/src/views/workflow/` | 宸ヤ綔娴佺紪杈戝櫒/鍒楄〃/鎵ц/鐗堟湰瀵规瘮锛? 鏂囦欢锛?|
| NL 宸ヤ綔娴?| `Frontend/src/views/nl-workflow/Creator.vue` | NL 杞伐浣滄祦鍒涘缓鍣?|
| 浠ｇ爜鍥捐氨 | `Frontend/src/views/codegraph/` | 浠ｇ爜鍥捐氨鍙鍖栵紙7 鏂囦欢锛?|
| 璁粌 | `Frontend/src/views/training/` | YOLO 璁粌杩涘害闈㈡澘锛? 鏂囦欢锛?|
| 璁剧疆 | `Frontend/src/views/settings/` | 璁剧疆/璁¤垂/鍝佺墝/闆嗘垚/妗岄潰Agent锛? 鏂囦欢锛?|
| 鏁版嵁闆?| `Frontend/src/views/datasets/` + `dataset/` | 鏁版嵁闆嗘祻瑙?鏍囨敞/鎺ㄨ崘锛? 鏂囦欢锛?|
| 鐭ヨ瘑搴?| `Frontend/src/views/knowledge/` | RAG 鐭ヨ瘑搴擄紙2 鏂囦欢锛?|
| 鍚戦噺瀛樺偍 | `Frontend/src/views/vector-store/` | 鍚戦噺瀛樺偍绠＄悊锛? 鏂囦欢锛?|
| 鎻愮ず璇?| `Frontend/src/views/prompt/List.vue` | 鎻愮ず璇嶅垪琛?|
| 妯″瀷 | `Frontend/src/views/model/Index.vue` | 妯″瀷绠＄悊 |
| 妯℃澘甯傚満 | `Frontend/src/views/marketplace/` | 妯℃澘甯傚満/璇︽儏/鎴戠殑妯℃澘锛? 鏂囦欢锛?|
| 鍥㈤槦 | `Frontend/src/views/team/Index.vue` | 鍥㈤槦绠＄悊 |
| 鐩戞帶 | `Frontend/src/views/monitoring/Index.vue` | 鐩戞帶闈㈡澘 |
| 鎵ц鍘嗗彶 | `Frontend/src/views/execution/History.vue` | 鎵ц鍘嗗彶 |
| 钀藉湴椤?| `Frontend/src/views/Landing.vue` | 棣栭〉钀藉湴椤?|
| 404 | `Frontend/src/views/NotFound.vue` | 404 椤甸潰 |

**閰嶇疆鏂囦欢**锛歚package.json`銆乣vite.config.js`銆乣tsconfig.json`銆乣tsconfig.node.json`銆乣vitest.config.ts`銆乣playwright.config.js`銆乣.eslintrc.cjs`銆乣.env.example`銆乣.env.production`

**娴嬭瘯**锛歚Frontend/tests/`锛圗2E + 鍗曞厓娴嬭瘯 + mocks锛?
---

### 3. 妗岄潰搴旂敤锛圗lectron Desktop锛?
> 璺緞锛歚Desktop/`

| 鏂囦欢 | 璇存槑 |
|------|------|
| `main.js` | Electron 涓昏繘绋?|
| `preload.js` | 棰勫姞杞借剼鏈?|
| `electron.html` | 绐楀彛椤甸潰 |
| `package.json` | 渚濊禆閰嶇疆 |
| `assets/README.md` | 璧勬簮鐩綍璇存槑 |

---

### 4. 椤圭洰鏂囨。锛圖ocs锛?
> 璺緞锛歚Docs/` 鈥?鍏?50+ 浠芥枃妗?
| 瀛愮洰褰?| 璇存槑 | 鏂囦欢鏁?|
|--------|------|--------|
| `Docs/project-audits/` | 椤圭洰瀹¤锛氭灦鏋勫璁°€佽縼绉昏褰曘€侀鍩熻璁°€佽鍔ㄨ鍒掋€佽缁冨伐浣滄祦钃濆浘 | ~20 |
| `Docs/phases/` | 鍒嗛樁娈典紭鍖栬鍒掞紙Phase 0-5锛?| 6 |
| `Docs/tasks/` | 鍥㈤槦浠诲姟鍒嗛厤锛圱ASK-001 鑷?006锛?| 7 |
| `Docs/api/` | API 瑙勮寖鏂囨。銆佷竴鑷存€ф寚鍗椼€佸揩閫熷弬鑰?| 4 |
| `Docs/guides/` | 閮ㄧ讲/鏈湴寮€鍙戞寚鍗?| 2 |
| `Docs/superpowers/` | 寮€鍙戣鍒掍笌楠岃瘉 | 2 |
| `Docs/archive/student-assignments/` | 瀛︾敓浣滀笟褰掓。 | 6 |
| `Docs/杞欢钁椾綔鏉?` | 杞憲鐢宠鏉愭枡 | 3 |
| `Docs/` 鏍圭洰褰?| 椤圭洰鎵ц绱㈠紩銆佹敼杩涜鍒掋€佺粨鏋勬枃妗ｃ€佺瓟杈╅棶棰樺簱 | 5 |

---

### 5. 姣曚笟璁烘枃锛圱hesis锛?
> 璺緞锛歚Thesis/` 鈥?姣曚笟璁烘枃鍏ㄥ鏉愭枡

| 瀛愮洰褰?| 璇存槑 | 鏂囦欢鏁?|
|--------|------|--------|
| `Thesis/chapter/` | 璁烘枃绔犺妭 00-09锛堟憳瑕佲啋鎬荤粨灞曟湜锛?| 10 |
| `Thesis/figures/` | 鍥捐〃璇存槑鏂囨。 | 5 |
| `Thesis/experiments/` | 瀹為獙鑴氭湰涓庤瘎浼版暟鎹?| 5 |
| `Thesis/references/` | 鍙傝€冩枃鐚瑪璁?| 1 |
| 鏍圭洰褰?| 璁烘枃鑽夌 v1銆丷EADME | 2 |

---

### 6. PPT 婕旂ず

> 璺緞锛歚PPT/`

| 鏂囦欢 | 璇存槑 |
|------|------|
| `Flowly_NL2WF_鍙傝禌浣滃搧.pptx` | 鍙傝禌婕旂ず鏂囩 |
| `check_table.py` | PPT 鏁版嵁妫€鏌ヨ剼鏈?|
| `qa_check.py` | QA 妫€鏌ヨ剼鏈?|
| `generate.js` | PPT 鐢熸垚杈呭姪鑴氭湰 |
| `package.json` + `package-lock.json` | Node 渚濊禆 |

---

### 7. 娴嬭瘯浠ｇ爜

> 璺緞锛歚tests/`

| 瀛愮洰褰?| 璇存槑 |
|--------|------|
| `tests/frontend/unit/` | 鍓嶇 API 鍗曞厓娴嬭瘯锛?5 涓?spec锛?|
| `tests/frontend/` 鏍?| Jest 閰嶇疆 |
| `tests/nl_workflow/` | NL 宸ヤ綔娴佹祴璇曪紙鍚?conftest锛? 涓祴璇曪級 |
| `tests/` 鏍圭洰褰?| `debug_auth.py`銆乣debug_conv.py`銆乣debug_conv2.py`銆乣test_agent_comprehensive.py` 鈥?**涓存椂璋冭瘯鏂囦欢** |

---

### 8. 娴嬭瘯鎶ュ憡涓庢埅鍥?
> 璺緞锛歚tests/artifacts/acceptance/`銆乣tests/artifacts/manual-screenshots/`銆乣Backend/reports/`銆乣Frontend/tests/artifacts/manual-screenshots/`

| 璺緞 | 鍐呭 | 寤鸿 |
|------|------|------|
| `tests/artifacts/acceptance/` | NL 妯″潡 E2E 娴嬭瘯鎶ュ憡 + 12 寮犳埅鍥?| 褰掓。鍚庡彲娓呯悊 |
| `tests/artifacts/manual-screenshots/` | 涓昏鍥炬祴璇曟埅鍥撅紙5 寮狅級 | 褰掓。鍚庡彲娓呯悊 |
| `Backend/reports/` | 5 涓?API 妫€鏌?JSON 鎶ュ憡锛?026-05-10锛?| 涓存椂鏂囦欢锛屽彲鍒犻櫎 |
| `Frontend/tests/artifacts/manual-screenshots/` | 澶辫触娴嬭瘯鐨勬埅鍥俱€佽棰戙€侀敊璇棩蹇?| 淇鍚庡彲娓呯悊 |

---

### 9. CI/CD 涓?Docker

> 璺緞锛歚docker/`銆乣.github/`

| 璺緞 | 璇存槑 |
|------|------|
| `.github/workflows/ci.yml` | GitHub Actions CI 閰嶇疆 |
| `docker/Dockerfile.backend` | 鍚庣 Dockerfile |
| `docker/Dockerfile.frontend` | 鍓嶇 Dockerfile |
| `docker/Dockerfile.nginx` | Nginx Dockerfile |
| `docker/.env.example` | Docker 鐜鍙橀噺绀轰緥 |

---

### 10. 鑴氭湰涓庡伐鍏?
> 璺緞锛歚Scripts/`

| 鏂囦欢 | 璇存槑 |
|------|------|
| `setup.bat` | 鐜鍒濆鍖栬剼鏈?|
| `train_model.py` | 鐙珛璁粌鑴氭湰锛堜笌 Backend/scripts/train_model.py 鍐呭涓嶅悓锛?|

---

### 11. IDE/缂栬緫鍣ㄩ厤缃?
| 璺緞 | 璇存槑 |
|------|------|
| `.vscode/settings.json` | VS Code 宸ヤ綔鍖鸿缃?|
| `.idea/` | JetBrains IDE 閰嶇疆锛? 涓枃浠讹級 |
| `.cursor/rules/global-rules.md` | Cursor AI 瑙勫垯 |
| `.claude/settings.local.json` | Claude 鏈湴璁剧疆 |
| `.cursorrules` | Cursor 瑙勫垯锛堟牴鐩綍锛?|

---

### 12. 鏍圭洰褰曢厤缃枃浠?
| 鏂囦欢 | 璇存槑 |
|------|------|
| `README.md` | 椤圭洰璇存槑 |
| `AGENTS.md` | AI Agent 绾﹀畾 |
| `.gitignore` | Git 蹇界暐瑙勫垯 |
| `.env.example` | 鐜鍙橀噺绀轰緥 |
| `.env` | **瀹為檯鐜鍙橀噺锛堝惈瀵嗛挜锛?* |
| `.mcp.json` | MCP 閰嶇疆 |
| `pyrightconfig.json` | Python 绫诲瀷妫€鏌ラ厤缃?|
| `pytest.ini` | pytest 閰嶇疆 |
| `requirements.txt` | Python 渚濊禆锛堟牴鐩綍锛?|
| `requirements.in` | Python 渚濊禆澹版槑锛堟牴鐩綍锛屼笌 requirements.txt 鍔熻兘閲嶅锛?|
| `skills-lock.json` | 鎶€鑳介攣瀹氭枃浠讹紙鏍圭洰褰曪級 |

---

### 13. 铏氭嫙鐜涓庝緷璧栫紦瀛?
| 璺緞 | 璇存槑 |
|------|------|
| `.venv/` | Python 铏氭嫙鐜锛?00+ 鏂囦欢锛?|
| `Frontend/node_modules/` | 鍓嶇 Node 渚濊禆 |
| `Desktop/node_modules/` | Electron 渚濊禆 |
| `tests/frontend/node_modules/` | 娴嬭瘯 Node 渚濊禆 |

> 杩欎簺鐩綍搴旈€氳繃 `.gitignore` 绠＄悊锛屼笉搴旀彁浜ゅ埌鐗堟湰鎺у埗銆?
---

### 14. Playwright 娴忚鍣ㄥ綍鍒讹紙鍙竻鐞嗭級

> 璺緞锛歚.playwright-mcp/` 鈥?64 涓?YAML 鏂囦欢  
> 鏃堕棿鑼冨洿锛?026-05-10 07:36 ~ 09:56  
> 璇存槑锛氭祻瑙堝櫒鑷姩鍖栧綍鍒跺揩鐓э紝涓存椂璋冭瘯浜х墿

---

### 15. pytest 缂撳瓨

| 璺緞 |
|------|
| `.pytest_cache/` |
| `Backend/.pytest_cache/` |

> 鍙€氳繃 `.gitignore` 蹇界暐鎴栫洿鎺ュ垹闄ゃ€?
---

## 浜屻€侀噸澶嶆枃浠惰瘑鍒?
| 搴忓彿 | 鏂囦欢缁?| 绫诲瀷 | 璇存槑 |
|------|--------|------|------|
| 1 | `Backend/check_user.py` / `check_user2.py` / `check_user3.py` / `check_user4.py` | 涓存椂璋冭瘯 | 4 涓枃浠跺潎璋冭瘯鍚屼竴鐢ㄦ埛 `sucker`锛屽姛鑳介珮搴﹂噸鍙?|
| 2 | `Backend/test_login.py` / `test_login2.py` / `test_login3.py` / `test_login4.py` | 涓存椂璋冭瘯 | 4 涓枃浠舵祴璇曞悓涓€鐧诲綍娴佺▼锛岄€愭杩唬鐗堟湰 |
| 3 | `Backend/test_api_login.py` / `test_api_login2.py` / `test_api_login3.py` | 涓存椂璋冭瘯 | 3 涓枃浠舵祴璇?API 鐧诲綍 |
| 4 | `Backend/test_http_login.py` / `test_http_login2.py` | 涓存椂璋冭瘯 | 2 涓枃浠舵祴璇?HTTP 鐧诲綍 |
| 5 | `Backend/scan_passwords.py` / `scan_passwords2.py` | 涓存椂璋冭瘯 | 2 涓枃浠舵壂鎻忓瘑鐮佸搱甯岋紝`scan_passwords2.py` 涓虹簿绠€鐗?|
| 6 | `Scripts/train_model.py` vs `Backend/scripts/train_model.py` | 鍔熻兘閲嶅 | 鍚屼负璁粌鑴氭湰浣嗗唴瀹瑰樊寮傚ぇ锛涘缓璁繚鐣?Backend 鐗堟湰锛堝姛鑳芥洿鍏級锛孲cripts 鐩綍鏀逛负寮曠敤 |
| 7 | 鏍圭洰褰?`requirements.txt` vs `requirements.in` | 閰嶇疆鍐椾綑 | `requirements.in` 涓烘簮澹版槑锛宍requirements.txt` 涓洪攣瀹氱増鏈紱淇濈暀 `requirements.in`锛宍requirements.txt` 鐢?`pip-compile` 鐢熸垚 |
| 8 | 鏍圭洰褰?`skills-lock.json` vs `Frontend/skills-lock.json` | 閰嶇疆閲嶅 | 寤鸿浠呬繚鐣欎竴浠?|

---

## 涓夈€佸缓璁垹闄ょ殑鏂囦欢

### 楂樹紭鍏堢骇锛堝畨鍏?鏁忔劅淇℃伅锛?
| 鏂囦欢 | 鍘熷洜 |
|------|------|
| `Backend/password_hash.txt` | 鍖呭惈瀵嗙爜鍝堝笇鐗囨 `pbkdf2_sha256\`锛屽瓨鍦ㄥ畨鍏ㄩ殣鎮?|
| `.env` | 鍖呭惈瀹為檯瀵嗛挜閰嶇疆锛岀‘璁ゅ凡灏嗗繀闇€鍙橀噺杩佺Щ鍒?`.env.example` 鍚庡彲鍒犻櫎 |

### 涓紭鍏堢骇锛堜复鏃惰皟璇曡剼鏈?鈥?20 涓枃浠讹級

| 鏂囦欢鍒楄〃 |
|----------|
| `Backend/check_user.py` |
| `Backend/check_user2.py` |
| `Backend/check_user3.py` |
| `Backend/check_user4.py` |
| `Backend/test_login.py` |
| `Backend/test_login2.py` |
| `Backend/test_login3.py` |
| `Backend/test_login4.py` |
| `Backend/test_api_login.py` |
| `Backend/test_api_login2.py` |
| `Backend/test_api_login3.py` |
| `Backend/test_http_login.py` |
| `Backend/test_http_login2.py` |
| `Backend/scan_passwords.py` |
| `Backend/scan_passwords2.py` |
| `Backend/fix_password.py` |
| `Backend/test_hash.py` |
| `Backend/test_email_nl.py` |
| `tests/debug_auth.py` |
| `tests/debug_conv.py` |
| `tests/debug_conv2.py` |

> 璇存槑锛氬潎涓轰竴娆℃€ц皟璇曡剼鏈紝鍔熻兘宸茬敱姝ｅ紡娴嬭瘯瑕嗙洊銆傚闇€淇濈暀璁板綍锛屽缓璁Щ鍔ㄥ埌 `Docs/archive/debug-scripts/` 褰掓。鑰岄潪鐩存帴鍒犻櫎銆?
### 浣庝紭鍏堢骇锛堜复鏃朵骇鐗╀笌缂撳瓨锛?
| 璺緞 | 鏂囦欢鏁?| 璇存槑 |
|------|--------|------|
| `.playwright-mcp/` | 64 | 娴忚鍣ㄥ綍鍒跺揩鐓э紝璋冭瘯娈嬬暀 |
| `Backend/reports/api_check_*.json` | 5 | 涓存椂 API 妫€鏌ユ姤鍛?|
| `tests/artifacts/acceptance/*.png` | 12 | E2E 娴嬭瘯鎴浘锛堝彲褰掓。锛?|
| `tests/artifacts/manual-screenshots/*.png` | 5 | 娴嬭瘯鎴浘锛堝彲褰掓。锛?|
| `Frontend/tests/artifacts/manual-screenshots/` | 3 | 澶辫触娴嬭瘯瑙嗛/鎴浘/鏃ュ織 |
| `Frontend/vite-out.log` | 1 | Vite 鏋勫缓杈撳嚭鏃ュ織 |
| `Frontend/vite-err.log` | 1 | Vite 閿欒鏃ュ織 |
| `.pytest_cache/` (2 澶? | 鈥?| pytest 缂撳瓨鐩綍 |
| `tests/frontend/junit.xml` | 1 | 娴嬭瘯缁撴灉 XML |

---

## 鍥涖€佹暣鐞嗗缓璁紭鍏堢骇

### 绔嬪嵆澶勭悊
1. 鍒犻櫎 `Backend/password_hash.txt`
2. 灏?`.env` 浠庣増鏈帶鍒朵腑绉婚櫎锛堢‘璁?.gitignore 宸插寘鍚級
3. 娓呯悊 20 涓?Backend 鏍圭洰褰曚复鏃惰皟璇曡剼鏈?
### 鏈澶勭悊
4. 娓呯悊 `.playwright-mcp/` 鐩綍锛?4 涓?YAML锛?5. 娓呯悊 `Backend/reports/` 涓?5 涓复鏃?JSON
6. 鍒犻櫎 `Frontend/vite-out.log` 鍜?`Frontend/vite-err.log`
7. 娓呯悊 `.pytest_cache/` 鐩綍

### 鍙€変紭鍖?8. 鍚堝苟 `tests/artifacts/acceptance/` 鍜?`tests/artifacts/manual-screenshots/` 鐩綍
9. 缁熶竴 `requirements` 绠＄悊锛堜繚鐣?`.in`锛屽垹闄?`.txt` 鐢辩紪璇戠敓鎴愶級
10. 鍐冲畾 `skills-lock.json` 淇濈暀涓€浠?11. 鍚堝苟 `Scripts/train_model.py` 鍒?Backend 鐗堟湰鎴栨槑纭尯鍒嗙敤閫?12. 鏁寸悊 `Docs/archive/` 涓殑瀛︾敓浣滀笟褰掓。

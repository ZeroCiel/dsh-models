# dsh-models — DeepSeek Harness 全模型线路配置

把本机全部模型线路（10 个直连 provider + Magpie 网关 + xAI + DeepSeek 官方，共 14 条路由 / 58 个模型）导入 DeepSeek Harness（DSH）桌面版，**配置与密钥分离**：

- `cordis.patch.yml` — DSH 的配置源（只含 `apiKeyEnv` 变量名，**零密钥**，可直接推送 GitHub）
- `.env.example` — 变量名模板；真实密钥写在本地 `%USERPROFILE%\.dsh\.env`，永不入库
- `import_dsh_patch.py` — 一键从 opencode.json 重新生成/更新 patch 的导入脚本

## DSH 配置机制（调试结论，避免踩坑）

| 文件 | 角色 |
|---|---|
| `~/.dsh/profiles/desktop/cordis.patch.yml` | **真正生效的配置源**，`llm-pi-ai` 插件的 `providers` 字典在这里。官方注释：「Edit cordis.patch.yml, not this file」 |
| `~/.dsh/settings.yaml` | 遗留导入格式。启动时被 `dsh-settings` 改名为 `.imported` 并导入 profile patch，**手改无效且会被重置** |
| `~/.dsh/.env` | 密钥环境变量，`apiKeyEnv` 按请求经凭据 seam 解析，配置文件里永远没有密钥明文 |

`settings.yaml` → `.imported` → `.imported.kept` 的链条是 DSH 的**一次性遗留迁移**（`dsh-settings/lib/index.js` `importLegacyDocument()`），不是每次启动都跑；运行时模型列表来自 `cordis.patch.yml`。

## 使用步骤

1. 关闭 DeepSeek Harness（5 个进程全部退出）
2. 备份并替换：把 `cordis.patch.yml` 复制到 `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml`（先留 `.bak-*` 备份）
3. 把 `.env.example` 复制为 `%USERPROFILE%\.dsh\.env`，填入真实密钥（或按变量名追加到现有 `.env`）
4. 启动 DSH，模型选择器即出现全部线路

## 从 opencode.json 重新生成

线路在 opencode 侧更新后（加模型/换 key），一键同步：

```powershell
python import_dsh_patch.py
```

脚本行为：读 `%USERPROFILE%\.config\opencode\opencode.json` → 合并进 patch（保留 xai / magpie 等 opencode 没有的路由）→ 新密钥追加进 `.env` → **patch 全文密钥扫描，发现明文立即中止** → 写前备份、写后复检。

## 线路清单（58 个模型 / 14 路由）

| 路由 | 密钥变量 | 端点 | 模型数 |
|---|---|---|---|
| amd（AMD Radeon 免费） | `AMD_API_KEY` | developer.amd.com.cn | 6 |
| baizhi（百智云） | `BAIZHI_API_KEY` | ai-models.app.baizhi.cloud | 6 |
| magpie（本地网关） | `MAGPIE_GATEWAY_KEY` | 127.0.0.1:3425 | 13 |
| magpie-anthropic | `MAGPIE_GATEWAY_KEY` | 127.0.0.1:3425 | 14 |
| modelscope（魔搭免费） | `MODELSCOPE_API_KEY` | api-inference.modelscope.cn | 4 |
| moma（移动云免费） | `MOMA_API_KEY` | moma.cmecloud.cn | 3 |
| apinex | `APINEX_API_KEY` | api.apinex.bond | 3 |
| deepseek-official | `DEEPSEEK_OFFICIAL_KEY` | api.deepseek.com | 2 |
| gitcode（本地网关） | `GITCODE_API_KEY` | 127.0.0.1:13458 | 2 |
| xai | `XAI_API_KEY` | api.x.ai | 2 |
| zhipu（智谱免费） | `ZHIPU_API_KEY` | open.bigmodel.cn | 1 |
| scnet（SCNet） | `SCNET_API_KEY` | api.scnet.cn | 1 |
| tokenrouter | `TOKENROUTER_API_KEY` | api.tokenrouter.com | 1 |
| deepseek（官方账号路由） | `DEEPSEEK_API_KEY` | （目录路由，无自定义模型） | — |

## 回滚

- patch：还原 `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml.bak-<时间戳>`（脚本自动创建）
- `.env`：同理有 `.bak-<时间戳>` 备份
- DSH 设置界面里删掉对应 provider 路由也能逐条移除

## 安全边界

- 本仓库任何文件都不含真实密钥；CI 前可再跑一遍 `import_dsh_patch.py` 内置的前缀扫描
- `.env`、`*.bak-*` 已在 `.gitignore`；`.env.example` 只是占位模板

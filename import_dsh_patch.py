# -*- coding: utf-8 -*-
"""导入本机全部模型到 DSH：改 cordis.patch.yml（DSH 真正读取的配置源）。
- 从 opencode.json 读 provider/baseURL/models
- 只写 apiKeyEnv 变量名，密钥不进 patch（不进 GitHub）
- 保留 xai / magpie-anthropic 等 opencode.json 没有的 provider
- 备份 + YAML 校验 + 明文密钥检查 + 失败回滚
"""
import os, sys, json, shutil, datetime, yaml

HOME = os.environ["USERPROFILE"]
OPENCODE = os.path.join(HOME, ".config", "opencode", "opencode.json")
PATCH = os.path.join(HOME, ".dsh", "profiles", "desktop", "cordis.patch.yml")
ENVFILE = os.path.join(HOME, ".dsh", ".env")

# opencode provider -> (DSH provider key, env 变量名, 显示名, 是否已有 env)
MAP = [
    ("free-amd",          "amd",              "AMD_API_KEY",           "AMD Radeon Cloud",       True),
    ("zhipu",             "zhipu",            "ZHIPU_API_KEY",         "智谱 GLM 免费",           False),
    ("scnet",             "scnet",            "SCNET_API_KEY",         "SCNet",                   False),
    ("deepseek",          "moma",             "MOMA_API_KEY",          "MoMA 免费",              False),
    ("deepseek-official", "deepseek-official","DEEPSEEK_OFFICIAL_KEY",  "DeepSeek 官方",          False),
    ("modelscope",        "modelscope",       "MODELSCOPE_API_KEY",    "魔搭 ModelScope 免费",    False),
    ("baizhi",            "baizhi",           "BAIZHI_API_KEY",        "百智云",                  True),
    ("tokenrouter",       "tokenrouter",      "TOKENROUTER_API_KEY",   "TokenRouter",             False),
    ("gitcode-codingplan","gitcode",          "GITCODE_API_KEY",       "GitCode CodingPlan",      False),
    ("apinex",            "apinex",           "APINEX_API_KEY",        "APInex 免费",             False),
]

op = json.load(open(OPENCODE, encoding="utf-8-sig"))
op_providers = op.get("provider", {})

with open(PATCH, "r", encoding="utf-8") as f:
    patch_text = f.read()
patch = yaml.safe_load(patch_text)

# 找到 llm-pi-ai 插件节点
llm = None
for entry in patch:
    if isinstance(entry, dict) and entry.get("id") == "llm-pi-ai":
        llm = entry
        break
if llm is None:
    sys.exit("llm-pi-ai entry not found in cordis.patch.yml")
providers = llm["config"]["providers"]

# 原有 provider 名（保留不在 MAP 里的，如 deepseek/xai/magpie-anthropic）
original_keys = set(providers.keys())

added, updated = [], []
env_new = []
for src, target, envkey, disp, already in MAP:
    pr = op_providers.get(src)
    if not pr:
        print("skip %s: not in opencode.json" % src)
        continue
    base = pr.get("options", {}).get("baseURL", "")
    secret = pr.get("options", {}).get("apiKey", "")
    models = pr.get("models") or {}
    if not base or not models:
        print("skip %s: no baseURL/models" % src)
        continue
    block = {"displayName": disp, "apiKeyEnv": envkey,
             "api": "openai-completions", "baseURL": base, "models": []}
    for alias, m in models.items():
        if not isinstance(m, dict):
            continue
        mid = m.get("id") or alias
        name = str(m.get("name") or mid).split("(")[0].strip()
        ctx = int(m.get("contextWindow") or 131072)
        maxt = int(m.get("maxTokens") or 8192)
        mm = {"id": mid, "name": name, "contextWindow": ctx, "maxTokens": maxt,
              "input": ["text", "image"]}
        block["models"].append(mm)
    if not block["models"]:
        print("skip %s: no usable models" % src)
        continue
    block["streamIdleTimeoutMs"] = 600000
    if target in providers:
        updated.append(target)
    else:
        added.append(target)
    providers[target] = block
    if secret and secret.lower() != "none" and not already:
        env_new.append("%s=%s" % (envkey, secret))

# 校验：patch 里不能出现任何明文 key
out = yaml.safe_dump(patch, allow_unicode=True, sort_keys=False, default_flow_style=False)
for src, *_ in MAP:
    k = (op_providers.get(src, {}).get("options") or {}).get("apiKey", "")
    if k and k.lower() != "none" and k in out:
        sys.exit("ABORT: plaintext key for %s leaked into patch" % src)

recheck = yaml.safe_load(out)
llm2 = [e for e in recheck if isinstance(e, dict) and e.get("id") == "llm-pi-ai"][0]
assert len(llm2["config"]["providers"]) >= len(original_keys)

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(PATCH, PATCH + ".bak-" + stamp)
shutil.copy2(ENVFILE, ENVFILE + ".bak-" + stamp)

with open(PATCH, "w", encoding="utf-8", newline="") as f:
    f.write(out)
with open(PATCH, "r", encoding="utf-8") as f:
    verify = yaml.safe_load(f.read())
vllm = [e for e in verify if isinstance(e, dict) and e.get("id") == "llm-pi-ai"][0]
assert all(t in vllm["config"]["providers"] for t in added + updated)

if env_new:
    with open(ENVFILE, "r", encoding="utf-8") as f:
        et = f.read()
    if not et.endswith("\n"):
        et += "\n"
    et += "\n# DSH patch models - secrets, do NOT commit\n" + "\n".join(env_new) + "\n"
    with open(ENVFILE, "w", encoding="utf-8", newline="") as f:
        f.write(et)

print("backup stamp:", stamp)
print("added:", added)
print("updated:", updated)
print("kept original (not in opencode):", sorted(original_keys - set(t for _, t, *_ in MAP)))
print("total providers:", len(vllm["config"]["providers"]))
print("total models:", sum(len(v.get("models", [])) for v in vllm["config"]["providers"].values()))
print("env vars added:", len(env_new))
print("NO PLAINTEXT KEYS IN PATCH: OK")

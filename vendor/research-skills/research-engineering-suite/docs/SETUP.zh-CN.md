# 安装与更新

## 安装到 Codex 用户级 skills

Windows PowerShell：

```powershell
git clone https://github.com/JoeyJin-NJU/research-engineering-suite.git "$env:USERPROFILE\.codex\skills\research-engineering-suite"
```

如果你使用自定义 `CODEX_HOME`，把目标目录换成：

```powershell
git clone https://github.com/JoeyJin-NJU/research-engineering-suite.git "$env:CODEX_HOME\skills\research-engineering-suite"
```

## 更新

```powershell
cd "$env:USERPROFILE\.codex\skills\research-engineering-suite"
git pull
```

## 验证

新开 Codex 会话后测试：

```text
使用 $research-engineering-suite 帮我把一个科研任务拆成研究、写作、coding、debug、验证五个部分。
```

如果本机带有 Codex skill creator 校验脚本，可以运行：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" "$env:USERPROFILE\.codex\skills\research-engineering-suite"
```

预期输出：

```text
Skill is valid!
```

## 本地开发

这个仓库本身就是 skill 根目录。核心文件：

- `SKILL.md`
- `agents/openai.yaml`

修改后建议至少做三件事：

1. 检查 `SKILL.md` frontmatter 是否仍只有 `name` 和 `description`。
2. 运行 `quick_validate.py`。
3. 用一个真实科研任务试用，确认没有绕过 evidence/debug/verification gate。

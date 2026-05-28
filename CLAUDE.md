# CLAUDE.md — AI 助手指引

## 项目概述

DOCX 格式统一工具 — Windows 桌面应用，将格式不规范的 DOCX 按模板标准格式重新生成。

## 关键文件

| 文档 | 路径 |
|------|------|
| 开发需求 | `docs/requirements.md` |
| 技术规范 | `docs/tech-spec.md` |
| UI 设计规范 | `docs/design-spec.md` |
| 执行计划 | `docs/execution-plan.md` |
| 开发日志 | `dev-logs/YYYY-MM-DD.md` |

## 开发环境

- Python 3.8.6（`python` 命令，非 `python3`）
- python-docx 1.1.2、customtkinter 5.2.2、PyInstaller 3.6

## 编码约定

- 代码简洁，不过度抽象，不写多余注释
- 错误处理仅做在系统边界（用户输入/文件读取），内部模块信任调用方
- 面向用户的所有文案用中文
- 每次做且仅做一个步骤，验收通过再继续

## 每次代码变更后（强制）

对 `engine/`、`gui/`、`main.py` 的任何修改，按顺序完成以下 3 步：

1. **更新开发日志** `dev-logs/YYYY-MM-DD.md`：记录完成事项和技术决策；当天已有日志则追加「## 补充 — HH:MM」
2. **git commit**：英文简述"做了什么、为什么"，一个逻辑单元一个 commit
3. **重新打包 exe**：运行 `pyinstaller DOCX_Format_Unifier.spec` 和 `pyinstaller DOCX_Format_Unifier_debug.spec`，更新 `dist/` 中的两个 .exe

## 会话结束前

- 删除 `参考文件/` 中测试产生的临时文件（含 `test`、`_t`、`_debug`、`_temp` 等前缀/后缀）
- 仅保留 `Reference*` 开头的正式参考文件

## 约束

- 用户非技术人员，UI 简洁直观
- 参考文件不推到 GitHub
- 输出文件格式与模板一致

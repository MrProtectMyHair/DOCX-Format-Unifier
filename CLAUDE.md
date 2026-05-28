# CLAUDE.md — AI 助手指引

## 项目概述

这是一个 Windows 桌面应用项目，名为 **DOCX 格式统一工具**。帮助用户将格式不规范的 DOCX 文件按照模板文件的标准格式重新生成。

## 标准文件路径

| 文档 | 路径 | 说明 |
|------|------|------|
| 开发需求 | `docs/requirements.md` | 功能需求、非功能需求、用户场景 |
| 技术规范 | `docs/tech-spec.md` | 技术栈、模块设计、数据结构、算法 |
| UI 设计规范 | `docs/design-spec.md` | 窗口布局、组件规格、交互流程、颜色字体 |
| 执行计划 | `docs/execution-plan.md` | 分阶段任务、验收标准 |
| 开发日志 | `dev-logs/YYYY-MM-DD.md` | 每日开发记录 |
| 实施计划 | `C:\Users\Administrator\.claude\plans\windows-docx-input-docx-docx-ui-purrfect-balloon.md` | 总体实施计划 |

## 工作说明

### 开发流程

1. **开始新任务前**：读取 `docs/execution-plan.md` 确认当前阶段的依赖是否完成
2. **开发中**：严格按照 `docs/tech-spec.md` 中的模块设计和数据结构编码
3. **UI 相关**：参考 `docs/design-spec.md` 中的布局和颜色字体规范
4. **每日结束**：在 `dev-logs/YYYY-MM-DD.md` 中记录完成事项和待办事项

### 开发约定

1. **每次只完成一个步骤**：不跨步骤开发，确保每一步验收通过后再进入下一步
2. **代码风格**：简洁第一，不使用过度抽象
3. **注释**：仅对非显而易见的逻辑添加简短注释
4. **错误处理**：仅在系统边界（用户输入、文件读取）处做校验，内部模块信任调用方
5. **测试**：每个模块完成后，使用项目中 `参考文件/` 目录下的文件进行验证
6. **中文输出**：所有面向用户的日志、提示信息使用中文
7. **代码更改后即时存档**：
   - 每次有意义的代码变更完成后，同步更新 `dev-logs/YYYY-MM-DD.md` 中对应的完成事项和技术决策
   - 检查是否需要更新 `docs/` 中的相关规范文档（如算法变更需更新 `tech-spec.md`，UI 变更需更新 `design-spec.md`）
   - 及时做 git commit，提交信息用英文简述"做了什么、为什么"，方便随时回滚
   - commit 粒度：一个逻辑单元一个 commit（如一个模块完成、一个 bug 修复），不攒大量改动一次性提交
   - **代码更改后必须重新打包 .exe**：对 `engine/`、`gui/` 或 `main.py` 的任何修改，必须在 commit 后重新运行 `pyinstaller DOCX_Format_Unifier.spec` 和 `pyinstaller DOCX_Format_Unifier_debug.spec`，更新 `dist/` 中的两个 .exe 文件，否则用户下载到本地的 exe 仍是旧版本
8. **每次开发会话结束后**：
   - 更新 `dev-logs/YYYY-MM-DD.md`，记录本次会话的完成事项、技术决策、遇到的问题
   - 如果当天日志已存在，追加「补充」章节而非覆盖
9. **清理临时文件**：
   - 每次开发会话结束前，检查 `参考文件/` 目录，删除测试过程中产生的临时输出文件（命名含 `test`、`_t`、`_debug`、`_temp` 等前缀/后缀）
   - 仅保留 `Reference*` 开头的正式参考文件

### 开发环境

- Python 3.8.6（`python` 命令，非 `python3`）
- pip 已可用
- python-docx 1.1.2 已安装
- customtkinter 待安装

### 关键约束

- 用户是非技术人员，UI 必须简洁直观
- 最终产物为单个 .exe 文件
- 输出文件必须与模板文件的格式一致
- 参考文件位于 `参考文件/` 目录

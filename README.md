# DOCX 格式统一工具 (DOCX Format Unifier)

一款 Windows 桌面应用，将格式不规范的 DOCX 文件按照模板标准格式重新生成。

**输入**：一份内容正确但格式混乱的 DOCX + 一份格式标准的模板 DOCX  
**输出**：模板的格式 + 输入的文字内容

## 适用场景

- 多人协作的表格/文档格式不统一，需要批量规范化
- 审批表、合同书、辅导方案等固定格式文档的自动填表
- 模板中留有下划线空白占位，需自动从输入提取对应值填入

## 功能特性

### 智能内容匹配
- **段落匹配**：标签相似度优先（47 个常见中文字段），位置回退兜底
- **表格匹配**：列头引导 + 精确文本 + 标签全局匹配
- **多表格支持**：自动处理文档中的多个表格
- **手动映射**：高级用户可以手动调整输入列与模板列的对应关系

### 表单式段落填充
- 自动识别模板中的下划线/空白占位（如 `______`、`____`）
- 用固定文字作为锚点从输入提取对应值
- **保留原位的所有格式**：下划线、字体、字号、加粗

### 空值模板填充
- **标签领地**：每个标签管辖其右侧空单元格，直到下一个标签
- **列头引导**：纯数据行向上查找表头，按列映射填入
- 汇总标签（合计/总计/小计）智能限制填充范围
- 签章/行政关键词（签字、盖章、审批等）自动跳过

### 用户体验
- 简洁直观的 Professional Blue 主题 UI
- 全中文界面（标签、按钮、日志、对话框）
- 一键转换，实时日志反馈
- 打包为单个 `.exe`，无需安装任何依赖

## 快速开始

### 运行已打包的 exe
1. 从 `dist/` 下载 `DOCX_Format_Unifier.exe`
2. 双击运行
3. 选择输入文件、模板文件、输出位置
4. 点击「开始转换」

### 从源码运行
```bash
pip install -r requirements.txt
python main.py
```

### 打包为 exe
```bash
pyinstaller DOCX_Format_Unifier.spec        # 正式版（无控制台）
pyinstaller DOCX_Format_Unifier_debug.spec  # 调试版（带控制台）
```

## 项目结构

```
├── main.py              # 入口
├── engine/
│   ├── reader.py        # DOCX 读取模块
│   ├── matcher.py       # 智能匹配引擎
│   └── writer.py        # DOCX 生成模块（格式化填充）
├── gui/
│   ├── main_window.py   # 主窗口（Professional Blue）
│   └── mapping_dialog.py # 手动映射弹窗
├── docs/                # 项目文档
│   ├── requirements.md  # 开发需求
│   ├── tech-spec.md     # 技术规范
│   ├── design-spec.md   # UI 设计规范
│   └── execution-plan.md # 执行计划
├── dev-logs/            # 开发日志
├── tests/               # 测试脚本
├── skills/              # AI 辅助 skill
├── 参考文件/             # 测试用参考文件（不推 GitHub）
└── dist/                # 打包后的 exe
```

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.8.6 |
| DOCX 库 | python-docx | 1.1.2 |
| GUI | customtkinter | 5.2.2 |
| 打包 | PyInstaller | 3.6 |

## 开发

- 开发流程和编码约定见 [CLAUDE.md](CLAUDE.md)
- 功能需求见 [docs/requirements.md](docs/requirements.md)
- 技术细节见 [docs/tech-spec.md](docs/tech-spec.md)
- 开发历程见 [dev-logs/](dev-logs/)

## 约束

- 仅支持 `.docx` 格式（Office Open XML）
- 运行环境：Windows 10 / Windows Server 2022+
- 参考文件目录 `参考文件/` 中的测试数据不上传 GitHub

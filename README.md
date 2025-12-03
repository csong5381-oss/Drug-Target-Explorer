# 🧬 Drug Target Explorer

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 Flask 的 Web 应用，用于药物靶点发现和 PubMed 文献智能分析。

## ✨ 主要功能

- 🔍 **药物靶点智能搜索** - 根据药物名称查询相关靶点
- 📚 **PubMed 文献检索** - 自动获取最新研究文献
- 🧠 **LLM 智能分析** - 使用 GPT 模型分析文献内容
- 🎨 **现代化 Web 界面** - 响应式设计，操作简便
- 📊 **结果可视化** - 清晰的搜索结果展示

## 🚀 快速开始

### 环境要求
- Python 3.8 或更高版本
- OpenAI API 密钥
- PubMed 邮箱账户（用于文献检索）

### 安装步骤

1. **克隆项目**
   \\\ash
   git clone https://github.com/csong5381-oss/Drug-Target-Explorer.git
   cd Drug-Target-Explorer
   \\\

2. **创建虚拟环境（推荐）**
   \\\ash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   \\\

3. **安装依赖**
   \\\ash
   pip install -r requirements.txt
   \\\

4. **配置 API 密钥**
   \\\ash
   # 创建配置目录
   mkdir config
   
   # 创建配置文件
   # 在 config/api_config.yaml 中添加：
   \\\yaml
   openai:
     api_key: \"你的-OpenAI-API-密钥\"
     model: \"gpt-4\"
   
   pubmed:
     email: \"你的邮箱@example.com\"
   \\\

5. **运行应用**
   \\\ash
   python app.py
   \\\

6. **访问应用**
   打开浏览器访问：http://localhost:5000

## 📁 项目结构

\\\
Drug-Target-Explorer/
├── app.py                    # Flask 主应用入口
├── requirements.txt          # Python 依赖包列表
├── .gitignore               # Git 忽略文件配置
│
├── src/                     # 核心业务模块
│   ├── drug_target_finder.py    # 药物靶点查找逻辑
│   ├── pubmed_client.py         # PubMed API 客户端
│   ├── llm_processor.py         # LLM 处理模块
│   └── main.py                  # 主逻辑整合
│
├── templates/               # HTML 模板文件
│   └── index.html           # 主页面
│
├── static/                  # 静态资源
│   ├── css/
│   │   └── style.css       # 样式表
│   └── js/
│       └── app.js          # 前端交互脚本
│
└── config/                  # ⚠️ 本地配置文件（不上传）
    ├── api_config.yaml      # API 密钥配置
    └── paths.yaml           # 路径配置
\\\

## 🔧 配置说明

### API 密钥获取

1. **OpenAI API**
   - 访问: https://platform.openai.com/api-keys
   - 创建新的 API 密钥
   - 复制密钥到 \config/api_config.yaml\

2. **PubMed API**
   - 访问: https://www.ncbi.nlm.nih.gov/account/
   - 注册账户获取 API 密钥（可选）
   - 至少需要提供邮箱地址

### 环境变量（可选）
也可以使用环境变量替代配置文件：
\\\ash
export OPENAI_API_KEY=\"你的密钥\"
export PUBMED_EMAIL=\"你的邮箱\"
\\\

## 🧪 使用示例

1. **启动应用后**，在首页输入药物名称（如 \"Aspirin\"）
2. **点击搜索**，系统将：
   - 查询相关药物靶点
   - 检索 PubMed 最新文献
   - 使用 AI 分析关键信息
3. **查看结果**，包括：
   - 靶点蛋白列表
   - 相关文献摘要
   - AI 分析总结

## 🔒 安全注意事项

⚠️ **重要**：配置文件包含敏感信息，请务必：
- 将 \config/\ 目录添加到 \.gitignore\
- 不要将 API 密钥提交到版本控制
- 在生产环境中使用环境变量
- 定期更新 API 密钥

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建功能分支 (\git checkout -b feature/AmazingFeature\)
3. 提交更改 (\git commit -m 'Add some AmazingFeature'\)
4. 推送到分支 (\git push origin feature/AmazingFeature\)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持与反馈

- 提交 Issue: [GitHub Issues](https://github.com/csong5381-oss/Drug-Target-Explorer/issues)
- 邮件联系: （你的邮箱）

## 🙏 致谢

- OpenAI 提供的 GPT API
- PubMed/NCBI 提供的文献数据库
- Flask 开发团队
- 所有贡献者和用户

---
⭐ **如果这个项目对你有帮助，请给个 Star！** ⭐

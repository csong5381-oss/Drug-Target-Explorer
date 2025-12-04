🧬 DrugTarget Explorer
https://img.shields.io/badge/Python-3.8+-blue.svg
https://img.shields.io/badge/Flask-2.3+-green.svg
https://img.shields.io/badge/License-MIT-yellow.svg
https://img.shields.io/github/stars/csong5381-oss/Drug-Target-Explorer.svg
https://img.shields.io/github/issues/csong5381-oss/Drug-Target-Explorer.svg

AI-Powered Drug Target Discovery System - Extract drug-target relationships from biomedical literature using dual AI models with voting system.

✨ Features
🔍 Intelligent Search
Dual AI Models: DeepSeek + GLM-4.6 for comprehensive analysis

Consensus Voting: Cross-validation with agreement scoring

Knowledge Graph: DrugBank integration for prior knowledge enhancement

Smart PubMed Search: Multi-strategy literature retrieval

📊 Advanced Visualization
Model Comparison Panel: Side-by-side AI model results

Voting Visualization: Interactive consensus display

Confidence Scoring: High/Medium/Low confidence levels

Source Tracking: Track targets to specific AI models

🎯 Core Capabilities
Standard Search: Single model (GLM-4.6) analysis

Advanced Analysis: Dual-model voting system

Real Results: Actual search results, not mock data

Export Function: CSV export with full details

🚀 Quick Start
Prerequisites
Python 3.8+

API Keys: DeepSeek & GLM-4.6

PubMed email account

Installation
bash
# Clone the repository
git clone https://github.com/csong5381-oss/Drug-Target-Explorer.git
cd Drug-Target-Explorer

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
mkdir config
cp config/api_config.yaml.example config/api_config.yaml
# Edit config/api_config.yaml with your API keys
Configuration
Edit config/api_config.yaml:

yaml
zhipu:
  ZHIPUAI_API_KEY: "your_glm_api_key_here"
  model: "glm-4.6"

deepseek:
  api_key: "your_deepseek_api_key_here"

pubmed:
  email: "your_email@example.com"
Run the Application
bash
python app.py
Open your browser and visit: http://localhost:5000

📖 Usage Guide
1. Standard Search
Uses GLM-4.6 model only

Quick analysis with PubMed articles

Suitable for basic drug-target discovery

2. Advanced Analysis 🚀
Dual AI models (DeepSeek + GLM-4.6)

Voting system for consensus targets

Knowledge graph enhancement

Higher confidence results

3. Debug Mode 🐛
Simulated data for testing

Quick UI verification

No API calls required

4. Results Features
Voting Display: See which models identified each target

Confidence Levels: High (🔴), Medium (🟡), Low (⚪)

Source Tracking: 🤖 DeepSeek, 🧠 GLM-4.6, or Both ✓

Export: Download results as CSV

🏗️ Project Structure
text
Drug-Target-Explorer/
├── app.py                    # Main Flask application
├── ui.html                   # Modern web interface
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── config/                   # Configuration files
│   ├── api_config.yaml      # API keys and settings
│   ├── paths.yaml           # File paths configuration
│   └── config.py            # Configuration loader
│
├── src/                      # Core modules
│   ├── drug_target_finder.py    # Main search logic
│   ├── pubmed_client.py         # PubMed API integration
│   ├── llm_processor.py         # AI model processor
│   ├── multi_model_voter.py     # Dual-model voting system
│   ├── knowledge_graph_client.py # External data integration
│   └── kg_enhancer.py           # Knowledge graph enhancement
│
├── data/                     # Generated data
│   └── output/              # Analysis results
│
├── logs/                    # Application logs
└── cache/                   # Cached data
🔧 Technical Details
AI Models Used
DeepSeek: General-purpose model for biomedical analysis

GLM-4.6: Specialized model with domain knowledge

Voting Algorithm
python
# Key features:
1. Target normalization and matching
2. Jaccard similarity calculation
3. Confidence level assignment
4. Consensus identification
Search Strategies
Multi-strategy PubMed search

Language detection and filtering

Smart article selection

Batch processing with retry logic

🌐 API Endpoints
Endpoint	Method	Description
/	GET	Main web interface
/api/standard_search	POST	Standard single-model search
/api/advanced_search	POST	Dual-model advanced search
/api/debug/search	POST	Debug mode with simulated data
/api/export	POST	Export results as CSV
/api/health	GET	System health check
/api/system_status	GET	Detailed system status
🚢 Deployment
Local Development
bash
python app.py
Production Deployment
See DEPLOYMENT.md for detailed instructions on:

Gunicorn + Nginx setup

HTTPS configuration

Systemd service management

Performance optimization

Docker Deployment
bash
docker build -t drugtarget-explorer .
docker run -p 5000:5000 drugtarget-explorer
📊 Screenshots
Main Interface
https://screenshots/main-interface.png

Voting Results
https://screenshots/voting-results.png

Advanced Search
https://screenshots/advanced-search.png

🤝 Contributing
We welcome contributions! Please see CONTRIBUTING.md for details.

Development Setup
bash
# Fork and clone the repository
git clone https://github.com/your-username/Drug-Target-Explorer.git
cd Drug-Target-Explorer

# Create a feature branch
git checkout -b feature/amazing-feature

# Make your changes and commit
git commit -m 'Add amazing feature'

# Push to your fork
git push origin feature/amazing-feature

# Create a Pull Request
Code Style
Follow PEP 8 for Python code

Use meaningful variable names

Add docstrings for functions

Include type hints where possible

🐛 Troubleshooting
Common Issues
API Key Errors

text
Ensure API keys are correctly configured in config/api_config.yaml
PubMed Connection Issues

text
Check your internet connection and PubMed API status
Verify email configuration in pubmed settings
Import Errors

text
Make sure all dependencies are installed: pip install -r requirements.txt
Verify Python version is 3.8+
Getting Help
Check the Issues page

Create a new issue with detailed description

Include error messages and logs

📈 Performance
Search Time: 10-30 seconds depending on literature volume

Accuracy: Enhanced by dual-model consensus

Scalability: Batch processing and caching

Memory Usage: Optimized for typical server configurations

🔒 Security
API keys stored in separate configuration files

Input validation and sanitization

Rate limiting on external API calls

Recommended to use HTTPS in production

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
OpenAI for GPT API inspiration

PubMed/NCBI for biomedical literature access

DeepSeek and GLM for AI model APIs

Flask and Python communities

📞 Contact
GitHub Issues: Report Bugs

Email: csong5381@gmail.com

Project Link: https://github.com/csong5381-oss/Drug-Target-Explorer

⭐ Support the Project
If you find this project useful, please give it a ⭐ on GitHub!

Made with ❤️ for biomedical research community

Note: This tool is for research purposes only. Always verify drug-target relationships through proper scientific validation.


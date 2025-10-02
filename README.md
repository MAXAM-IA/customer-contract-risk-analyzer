# AI-CC-Risk-Analyzer 🤖⚖️

Intelligent contract analysis platform with automatic legal risk detection powered by LLMs (Gemini).

## 🚀 Key Features

- **Multimodal Analysis**: Supports PDF files and plain text
- **Integrated LLM**: Uses Google Gemini for advanced insights
- **Risk Assessment**: Automatic classification (High/Medium/Low)
- **Web Interface**: Streamlit frontend backed by a FastAPI service
- **Detailed Logging**: Full tracing of every analysis step
- **Asynchronous Processing**: Background jobs with real-time progress tracking

## 📋 Prerequisites

- Python 3.8 or newer
- Google API Key for Gemini
- Git

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone [repository]
cd ai-cc-risk-analyzer
```

### 2. Run the installation script
```bash
./install.sh
```
Or manually:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file at the project root:
```bash
cp .env.example .env
```

Edit `.env` and add your Google API Key:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

To generate an API key:
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Paste it into `.env`

### 4. Verify the setup
```bash
python test_system.py
```

## 🎯 Usage

### Quick start scripts

#### Method 1: Automated scripts
```bash
# Start the backend
./start_backend.sh

# In another terminal - launch the frontend
cd src && streamlit run main.py
```

#### Method 2: Manual launch
Terminal 1 - Backend:
```bash
cd fastapi_backend
uvicorn main:app --reload
```

Terminal 2 - Frontend:
```bash
streamlit run src/main.py
```

### Access points
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🧪 System Tests

### Full automated test
```bash
# 1. Start the backend in one terminal
./start_backend.sh

# 2. In another terminal, run the full test
python3 test_full_system.py
```

This script verifies:
- ✅ Backend connectivity
- ✅ System health check
- ✅ File upload and asynchronous analysis
- ✅ Polling (every 3 seconds just like the frontend)
- ✅ LLM processing
- ✅ Risk assessment

### Additional tests
```bash
# Backend-only test
python test_backend.py

# LLM-only test
python test_system.py
```

### Uploading and analyzing documents

1. **New Analysis**:
   - Open http://localhost:8501
   - Upload a PDF or text document
   - The system starts an asynchronous analysis with predefined questions
   - The frontend polls the backend every 3 seconds to display progress
   - Monitor the status in real time

2. **View Results**:
   - Detailed responses per question
   - Automatic risk evaluation (High/Medium/Low)
   - LLM-generated answers
   - Export options

3. **Re-analysis**:
   - Edit individual questions
   - Re-run the analysis with the modified questions
   - Compare results across runs

### Technical flow
1. Frontend uploads the file → Backend (`/analizar`)
2. Backend saves the file with its original extension
3. Worker starts an asynchronous background analysis
4. Frontend polls `/estado/{id}` every 3 seconds
5. Worker processes each question with Gemini LLM
6. The system updates granular progress
7. Frontend renders the final results

## 📊 Project Structure

```
ai-cc-risk-analyzer/
├── fastapi_backend/           # API Backend
│   ├── main.py               # API endpoints
│   ├── worker.py             # LLM analysis logic
│   ├── contratos/            # Uploaded files
│   ├── progreso/             # Analysis states
│   └── preguntas-risk-analyzer.xlsx
├── src/                      # Streamlit frontend
│   ├── main.py
│   ├── pages/
│   └── db/
├── requirements.txt          # Dependencies
├── test_system.py            # Validation script
├── install.sh                # Installation helper
└── .env.example              # Environment template
```

## 🔧 Advanced Configuration

### Available environment variables
```env
GOOGLE_API_KEY=your_key        # Required
LOG_LEVEL=INFO                 # Optional
PORT=8000                      # Optional
HOST=localhost                 # Optional
```

### Logging
Logs are stored in:
- `fastapi_backend/analisis.log` (detailed analysis log)
- Console output (real-time logs)

### Customizing questions
Edit `fastapi_backend/preguntas-risk-analyzer.xlsx` to change the analysis questions.

## ✅ System Validation

### Quick validation
```bash
# Check that everything is configured correctly
python3 validate_system.py
```

This script verifies:
- 📂 Required files
- 🔐 Environment variables
- 📦 Python dependencies
- 📁 Directory structure

### Full validation flow
```bash
# 1. Validate configuration
python3 validate_system.py

# 2. Start the backend
./start_backend.sh

# 3. Run the full system test
python3 test_full_system.py
```

## 🐛 Troubleshooting

### Issue: The analysis hangs
**Diagnose**:
```bash
# Check backend logs
tail -f fastapi_backend/analisis.log

# Check system status
curl http://localhost:8000/health
```
**Solution**: Inspect `analisis.log` and the console for specific errors.

### Issue: API Key error
```
❌ GOOGLE_API_KEY is not configured
```
**Solution**:
1. Run `python3 validate_system.py` for diagnostics
2. Confirm that `.env` exists and has the correct format
3. Make sure the API key is valid in [Google AI Studio](https://aistudio.google.com/app/apikey)
4. Restart the server

### Issue: Missing dependencies
**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: Questions file not found
**Solution**: Confirm that `fastapi_backend/preguntas-risk-analyzer.xlsx` exists.

### Issue: Frontend cannot reach the backend
**Check**:
```bash
# Is the backend running?
curl http://localhost:8000/health

# Any errors in the logs?
tail fastapi_backend/analisis.log
```

## 📝 API Endpoints

- `POST /analizar` - Start a new analysis
- `GET /estado/{id}` - Retrieve analysis progress
- `POST /reanalisar_pregunta/{id}/{num}` - Re-analyze a single question
- `POST /reanalisar_global/{id}` - Re-run all questions
- `GET /health` - System health status

## 🔄 Recent Updates

### v2.0 - LLM Integration
- ✅ Full integration with Google Gemini
- ✅ Multimodal analysis (PDF + text)
- ✅ Automatic risk evaluation
- ✅ Detailed logging
- ✅ Health checks
- ✅ Improved error handling

## 📞 Support

If you encounter issues:
1. Run `python test_system.py` for diagnostics
2. Inspect `analisis.log`
3. Review the API documentation at `/docs`

## 🔐 Security

- API keys are managed through environment variables
- Files are stored locally and temporarily
- Sensitive data is never written to public logs

---
*System developed for automated contract analysis with AI* 🤖⚖️

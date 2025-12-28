# Ariadne Health Agent

**Local-First, AI-Powered Health Intelligence.**

## Definition (What is this?)
Ariadne is your personal health data warehouse. It consolidates data from wearables (Garmin, Google Fit) and medical documents (PDFs, XMLs, Excel) into a local database. 

**Intelligence**: Powered by **Google Gemini 3 Flash Thinking**, offering "Systems Theory" analysis.
**Performance**: Uses SQLite Response Caching for <0.1s latency on repeated queries.

## Operation (How to use)

### 1. Launch
Double-click `START_APP.bat` to open the Chat Interface.

### 2. Add Data
Drop your files into the `00_Inbox` folder. The system is designed to grow with your data:
- **Medical Reports**: PDFs, Images.
- **Lab Results**: Excel (`.xlsx`).
- **Wearable Data**: Google Fit (CSV), Garmin (JSON, TCX).
- **Raw Exports**: XML / Health Connect.
- **Standards**: Ready for future formats like **EHRxF**.

### 3. Process
In the App sidebar, click **"Process New Files"**.
- Valid files are processed and moved to `01_Archive`.
- Issues are flagged in `00_Inbox/Errors`.

### 4. Chat
Ask questions like:
- *"How has my deep sleep changed over the last year?"*
- *"Show me a graph of my steps vs calories."*

## Structure (Where things are)
- `00_Inbox`: **Input**. Drop files here.
- `01_Archive`: **Storage**. Processed files.
- `02_Database`: **Data**. `health_data.db` lives here.
- `03_Apps`: **Code**. Python source code.
- `04_System`: **Config**. Docs and maintenance scripts.

## Requirements
- Python 3.10+
- Google Gemini API Key (stored in `.streamlit/secrets.toml`)

---
*For developer guidelines, see [Structure Guidelines](04_System/docs/Structure_Guidelines.md) (To be created/moved).*

# Execution Instructions

## Prerequisites
- Python 3.8+ installed.
- Internet access to `delfos.appsdevqa.equatorialenergia.com.br`.

## Setup
1. Open a terminal (PowerShell or CMD).
2. Navigate to the project folder:
   ```powershell
   cd C:\Users\Public\Downloads\EQT_LAB\Delfos\RPA_RelatoriosBD\Consulta-via-BFF
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Running the Bot
Execute the main script:
```powershell
python main.py
```

## Output
- **JSON files**: `SaidaRPA\Json`
- **Excel files**: `SaidaRPA\Excel`

## Configuration
- **Adding Endpoints**: Update `Modelos_EndPoits-BFF.txt` and run `python src/config_loader.py` to regenerate `config/endpoints.json`.
- **Environment Variables**: Edit `.env` to change settings like Base URL or tokens.

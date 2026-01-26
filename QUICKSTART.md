# Quick Start Guide

## For Windows Users

### One-Click Run

1. **Download the Project**
   - Open the project folder

2. **Run**
   - **Double-click** on `run.bat`
   - Packages will be installed automatically on first run (may take a few minutes)
   - Browser will open automatically

3. **Start Using**
   - `http://localhost:5000` will open in your browser
   - Application is ready!

### Initial Setup Steps

1. **Configure MySQL Bin Directory**
   - Click "Configure" button in the right panel
   - Enter the path to MySQL bin directory
   - Example: `C:/Program Files/mysql-5.7.44-winx64/bin`

2. **Add Database Connection**
   - Click "+ Add Connection" button in the left panel
   - Enter connection details:
     - Host: MySQL server address (e.g. 192.168.1.100)
     - Port: 3306 (default)
     - User: MySQL username
     - Password: MySQL password
     - Database: (optional) Specific database
   - Test connection with "Test Connection"
   - Save with "Add Connection"

3. **View Schemas**
   - Click on a connection in the left panel
   - All schemas will be listed in the middle panel

4. **Clone a Schema**
   - Right-click on a schema
   - Select "Duplicate"
   - Enter new schema name (e.g. `backup_6f`)
   - Click "Start Clone" button
   - Monitor progress

### Troubleshooting

**Python not found error:**
- Python 3.8 or higher must be installed
- Add Python to PATH or use full path

**Package installation error:**
- Check your internet connection
- Run manually:
  ```cmd
  pip install -r requirements.txt
  ```

**Port already in use:**
- Another application might be using port 5000
- You can change port number in `main.py`

### Stopping

- Press `Ctrl+C` in terminal window
- Or close the terminal window

## For Linux/Mac Users

```bash
# Run
python run.py

# or

python -m src.db_clone_tool.main
```

Open `http://localhost:5000` in browser.

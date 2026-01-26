# DBC-2: MySQL Binary Path Standardization & Multi-Platform Deployment

## Task Definition

### 📋 Mevcut Durum
MySQL binary'leri şu anda kullanıcı tarafından manuel olarak seçilen veya indirilen dizine kaydediliyor:
- Default indirme yeri: `C:\Kodlar\DB-Clone-Tool\tmp\mysql\mysql-8.0.40-winx64\bin`
- Browser'da dosya path limitasyonları var (security)
- Sadece Windows için ZIP desteği var (Linux için .tar.xz extract edilemiyor)
- Cross-platform standardizasyon yok
- Docker desteği yok
- Shell script desteği yok (sadece run.bat var)

### 🎯 İstenen
1. **Standart Binary Path Yapısı**
   - Platform-agnostic, professional dizin yapısı
   - Browser limitlerini bypass eden çözüm
   - OS standartlarına uygun (Windows, Linux, macOS)
   - Portable/local install seçenekleri

2. **Cross-Platform Run Scripts**
   - ✅ run.bat (mevcut)
   - ❌ run.sh (yok - eklenecek)
   - Dependency check ve auto-install
   - Virtual environment management

3. **Docker Deployment**
   - docker-compose.yml
   - Multi-stage build (production-ready)
   - Volume mounting for data persistence
   - Environment variable configuration
   - Health checks

### 📝 Örnekler

**Mevcut durum:**
```
User downloads MySQL → C:\Kodlar\DB-Clone-Tool\tmp\mysql\mysql-8.0.40-winx64\bin
Config saved → config.local/config.json: {"mysql_bin_path": "..."}
```

**İstenen durum (Platform-specific defaults):**

**Windows:**
```
%LOCALAPPDATA%\db-clone-tool\mysql\bin  (portable mode)
C:\ProgramData\db-clone-tool\mysql\bin  (system-wide install)
```

**Linux/macOS:**
```
~/.local/share/db-clone-tool/mysql/bin  (user install)
/opt/db-clone-tool/mysql/bin           (system install)
/usr/local/bin                         (system MySQL fallback)
```

**Docker:**
```
/app/mysql/bin (container internal path)
```

### 🧪 Test Senaryoları

**TS-1: Windows Portable Install**
- Given: Windows kullanıcısı ilk defa app açıyor
- When: MySQL download tıklanır
- Then: `%LOCALAPPDATA%\db-clone-tool\mysql` dizinine otomatik install edilmeli
- And: Config otomatik kaydedilmeli
- And: Permission error olmamalı

**TS-2: Linux User Install**
- Given: Linux kullanıcısı sudo yetkisi yok
- When: MySQL download seçilir
- Then: `~/.local/share/db-clone-tool/mysql` dizinine install edilmeli
- And: .tar.xz dosyası extract edilebilmeli
- And: Executables çalıştırılabilir olmalı

**TS-3: Docker Deployment**
- Given: docker-compose.yml dosyası var
- When: `docker-compose up` çalıştırılır
- Then: Container başlamalı
- And: MySQL binaries container içinde olmalı
- And: Bağlantılar persistent volume'da saklanmalı
- And: Health check pass etmeli

**TS-4: run.sh Cross-Platform**
- Given: Linux/macOS sistem
- When: `./run.sh` çalıştırılır
- Then: Virtual environment oluşturulmalı/activate edilmeli
- And: Dependencies install edilmeli
- And: Flask app başlamalı
- And: Browser açılmalı (opsiyonel)

**TS-5: Browser Limitation Bypass**
- Given: Kullanıcı custom path kullanmak istiyor
- When: Path input'a "C:\MySQL\bin" girilir
- Then: Path validation yapılmalı
- And: Invalid path durumunda friendly error mesajı gösterilmeli
- And: Valid path durumunda config kaydedilmeli

### ⚠️ Error Cases

**EC-1: Permission Denied**
```
Hata: "Permission denied creating directory C:\Program Files\db-clone-tool"
Çözüm: Fallback to %LOCALAPPDATA% veya kullanıcıya portable path öner
```

**EC-2: Linux Extract Failure**
```
Hata: ".tar.xz extraction not implemented"
Çözüm: tarfile module ile .tar.xz desteği ekle
```

**EC-3: Docker MySQL Binary Missing**
```
Hata: Container içinde mysqldump bulunamıyor
Çözüm: Multi-stage build ile MySQL official image'dan binary'leri copy et
```

**EC-4: Config Migration**
```
Hata: Eski config dosyası yeni standarda uymuyor
Çözüm: Migration script ile eski config'i yeni formata convert et
```

---

## Preanalysis

### 🔍 Mevcut Yapı Analizi

**Dosya Yapısı:**
```
C:\Kodlar\DB-Clone-Tool\
├── src/db_clone_tool/
│   ├── config.py              # Config management (BASE_DIR, CONFIG_DIR)
│   ├── mysql_download.py      # MySQL download/extract/validate
│   ├── routes/api.py          # /api/mysql/download endpoint
│   └── ...
├── run.bat                    # Windows launcher
├── tmp/mysql/                 # Current default download location
├── config.local/config.json   # MySQL bin path configuration
└── ...
```

**Key Code Locations:**

1. **MySQL Download Logic** (`mysql_download.py:53-102`):
   ```python
   def download_mysql(version, destination):
       # Platform detection
       is_windows = os.name == 'nt'
       # URL construction (Windows: ZIP, Linux: tar.xz)
       # Download with progress tracking
       # Returns zip_path
   ```

2. **Extract Logic** (`mysql_download.py:115-143`):
   ```python
   def extract_mysql(zip_path, destination):
       # ❌ PROBLEM: Only supports ZIP (Windows)
       # Linux .tar.xz not supported
       with zipfile.ZipFile(zip_path, 'r') as zip_ref:
           zip_ref.extractall(destination)
   ```

3. **Default Path Determination** (`routes/api.py:535-538`):
   ```python
   if destination:
       dest_dir = Path(destination)
   else:
       dest_dir = BASE_DIR / 'tmp' / 'mysql'  # ❌ Not platform-aware
   ```

4. **Config Storage** (`config.py:14-29`):
   ```python
   CONFIG_DIR = BASE_DIR / "config.local"
   CONFIG_FILE = CONFIG_DIR / "config.json"
   # ❌ Hardcoded relative to project dir, not user home
   ```

### 🔬 Teknik Analiz

**Platform Detection:**
- ✅ Uses `os.name == 'nt'` for Windows detection
- ❌ No macOS-specific handling
- ❌ No architecture detection (x86_64 vs ARM)

**Path Handling:**
- ✅ Uses `pathlib.Path` for cross-platform paths
- ✅ HTML accepts forward slashes (`C:/mysql/bin`)
- ❌ Error messages expose internal paths
- ❌ No path traversal protection

**Extraction Support:**
| Format | Windows | Linux |
|--------|---------|-------|
| .zip   | ✅      | ✅    |
| .tar.xz| ❌      | ❌    |

**Configuration:**
- ✅ JSON-based config (`config.local/config.json`)
- ❌ No environment variable support
- ❌ No XDG Base Directory spec compliance (Linux)
- ❌ No migration mechanism

**Browser Limitations:**
- HTML `<input type="file">` can't browse directories (only files)
- JavaScript can't access filesystem paths (security)
- Current solution: Manual text input (`<input type="text">`)
- ✅ Works but UX is poor

### 📊 Best Practice Uygunluğu

**OS Directory Standards:**

| Platform | User Data | App Data | System-Wide |
|----------|-----------|----------|-------------|
| Windows  | `%LOCALAPPDATA%` | `%APPDATA%` | `C:\ProgramData` |
| Linux    | `~/.local/share` | `~/.config` | `/opt`, `/usr/local` |
| macOS    | `~/Library/Application Support` | `~/Library/Preferences` | `/usr/local` |

**Current Status:**
- ❌ Uses project-relative paths (`tmp/mysql`)
- ❌ No adherence to OS standards
- ❌ Not suitable for installed package (assumes writable CWD)

**Docker Best Practices:**
- ❌ No Dockerfile
- ❌ No docker-compose.yml
- ❌ No multi-stage build
- ❌ No health checks
- ❌ No environment variable config

**Shell Script Best Practices:**
- ✅ run.bat exists (Windows)
- ❌ No run.sh (Linux/macOS)
- ❌ No dependency checking
- ❌ No error handling for missing Python

### ⚖️ Teknik Borç

**High Priority:**
1. Linux .tar.xz extraction not implemented → Schema clone fails on Linux
2. Hardcoded `tmp/mysql` path → Permission errors on system-wide installs
3. No Docker deployment → Can't deploy in containerized environments

**Medium Priority:**
4. No run.sh → Linux users must manually run Python commands
5. No environment variable config → Can't configure via CI/CD
6. Browser path input UX → Users confused about manual path entry

**Low Priority:**
7. No config migration → Breaking changes require manual fix
8. No XDG compliance → Linux power users expect `~/.config`

---

## Solution Suggestions

### 🅰️ Plan A: Minimal Platform-Aware Defaults (Quick Win)

**Scope:**
- Platform-specific default paths
- Linux .tar.xz extraction support
- run.sh script
- Basic Docker support (single-stage)

**Implementation:**

1. **Default Path Resolution** (`config.py`):
   ```python
   def get_default_mysql_dir():
       if os.name == 'nt':  # Windows
           return Path(os.environ['LOCALAPPDATA']) / 'db-clone-tool' / 'mysql'
       else:  # Linux/macOS
           return Path.home() / '.local' / 'share' / 'db-clone-tool' / 'mysql'
   ```

2. **Extract Support** (`mysql_download.py`):
   ```python
   import tarfile

   def extract_mysql(archive_path, destination):
       if archive_path.endswith('.tar.xz'):
           with tarfile.open(archive_path, 'r:xz') as tar:
               tar.extractall(destination)
       elif archive_path.endswith('.zip'):
           with zipfile.ZipFile(archive_path, 'r') as zip_ref:
               zip_ref.extractall(destination)
   ```

3. **run.sh**:
   ```bash
   #!/bin/bash
   echo "Starting DB Clone Tool..."
   python3 --version || { echo "Python 3.8+ required"; exit 1; }
   [ -d "venv" ] || python3 -m venv venv
   source venv/bin/activate
   pip install -e . > /dev/null 2>&1
   python -m src.db_clone_tool.main
   ```

4. **docker-compose.yml** (Basic):
   ```yaml
   version: '3.8'
   services:
     db-clone-tool:
       build: .
       ports:
         - "5000:5000"
       volumes:
         - ./config.local:/app/config.local
   ```

**Pros:**
- ✅ Quick implementation (1-2 days)
- ✅ Fixes critical Linux issue
- ✅ Minimal code changes
- ✅ No breaking changes for existing users

**Cons:**
- ❌ Basic Docker (single-stage, no optimization)
- ❌ No environment variable config
- ❌ No migration for existing configs

---

### 🅱️ Plan B: Full Multi-Platform Architecture (Comprehensive)

**Scope:**
- Everything in Plan A +
- XDG Base Directory compliance (Linux)
- Environment variable configuration
- Multi-stage Docker build
- Config migration
- Installation modes (portable vs system-wide)
- Health checks & monitoring

**Implementation:**

1. **Advanced Path Resolution** (`config.py`):
   ```python
   def get_default_mysql_dir(install_mode='portable'):
       if os.name == 'nt':
           if install_mode == 'system':
               return Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'db-clone-tool' / 'mysql'
           return Path(os.environ['LOCALAPPDATA']) / 'db-clone-tool' / 'mysql'
       else:
           # XDG Base Directory spec
           xdg_data_home = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
           if install_mode == 'system':
               return Path('/opt/db-clone-tool/mysql')
           return Path(xdg_data_home) / 'db-clone-tool' / 'mysql'
   ```

2. **Environment Variable Config**:
   ```python
   # config.py
   MYSQL_BIN_PATH = os.environ.get('DB_CLONE_MYSQL_BIN', get_default_mysql_dir())
   CONFIG_DIR = os.environ.get('DB_CLONE_CONFIG_DIR', get_default_config_dir())
   ```

3. **Multi-stage Dockerfile**:
   ```dockerfile
   FROM mysql:8.0 as mysql-binaries

   FROM python:3.11-slim
   COPY --from=mysql-binaries /usr/bin/mysql* /app/mysql/bin/
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   ENV DB_CLONE_MYSQL_BIN=/app/mysql/bin
   HEALTHCHECK CMD curl -f http://localhost:5000/health || exit 1
   CMD ["python", "-m", "src.db_clone_tool.main"]
   ```

4. **Config Migration**:
   ```python
   def migrate_config():
       if old_config_exists():
           old_config = load_old_config()
           new_config = {
               'version': '2.0',
               'mysql_bin_path': old_config.get('mysql_bin_path'),
               'install_mode': 'portable'
           }
           save_config(new_config)
           backup_old_config()
   ```

5. **Advanced run.sh**:
   ```bash
   #!/bin/bash
   set -e

   # Check dependencies
   command -v python3 >/dev/null 2>&1 || { echo "Python 3.8+ required"; exit 1; }

   # Virtual environment
   if [ ! -d "venv" ]; then
       echo "Creating virtual environment..."
       python3 -m venv venv
   fi

   source venv/bin/activate

   # Dependencies
   if ! python -c "import flask, pymysql" 2>/dev/null; then
       echo "Installing dependencies..."
       pip install -e . --quiet
   fi

   # Run
   echo "Starting DB Clone Tool on http://localhost:5000"
   exec python -m src.db_clone_tool.main
   ```

**Pros:**
- ✅ Production-ready
- ✅ Industry standard compliance
- ✅ Environment variable config (CI/CD friendly)
- ✅ Optimized Docker image
- ✅ Smooth upgrade path (migration)

**Cons:**
- ❌ Longer implementation (3-5 days)
- ❌ More testing required
- ❌ Migration complexity

---

### 💡 Öneri

**Tavsiye: Plan A → Plan B (Phased Approach)**

**Gerekçe:**
1. Plan A kritik sorunları hızlıca çözer (Linux support, default paths)
2. Docker basic support ile deployment mümkün olur
3. Plan B'yi sonraki iterasyonda ekleyerek production-ready yaparız
4. Breaking change riski minimize edilir

**Rollout Strategy:**
- **Phase 1 (DBC-2)**: Plan A implementation
  - Linux .tar.xz support
  - Platform-aware defaults
  - run.sh script
  - Basic docker-compose
- **Phase 2 (DBC-3)**: Plan B enhancements
  - Environment variables
  - Multi-stage Docker
  - Config migration
  - XDG compliance

---

## Phase Breakdown

### 📦 Phase 1: Platform-Specific Defaults & Linux Support
**Goal:** Fix critical cross-platform issues

**Tasks:**
1. Implement `get_default_mysql_dir()` with OS detection
2. Update `routes/api.py` to use new default
3. Add tarfile support to `extract_mysql()`
4. Test on Windows and Linux
5. Update documentation

**Files to modify:**
- `src/db_clone_tool/config.py` (new function)
- `src/db_clone_tool/mysql_download.py` (extract logic)
- `src/db_clone_tool/routes/api.py` (default path usage)

**Tests:**
- ✅ TS-1: Windows Portable Install
- ✅ TS-2: Linux User Install
- ✅ TS-5: Browser Limitation Bypass

**Completion Criteria:**
- All tests pass on Windows AND Linux
- No permission errors on default path
- Linux .tar.xz extraction works

---

### 🐚 Phase 2: Cross-Platform Run Scripts
**Goal:** Enable Linux/macOS users to run app easily

**Tasks:**
1. Create `run.sh` with venv management
2. Add dependency checking
3. Add executable permissions (`chmod +x`)
4. Test on Linux and macOS
5. Update README with run.sh instructions

**Files to create:**
- `run.sh` (new file)

**Files to modify:**
- `README.md` (add run.sh instructions)
- `.gitignore` (ensure venv not committed)

**Tests:**
- ✅ TS-4: run.sh Cross-Platform

**Completion Criteria:**
- `./run.sh` works on fresh Linux/macOS install
- Virtual environment auto-created
- Dependencies auto-installed
- Flask app starts successfully

---

### 🐳 Phase 3: Docker Deployment
**Goal:** Enable containerized deployment

**Tasks:**
1. Create `Dockerfile` (single-stage for now)
2. Create `docker-compose.yml`
3. Add volume mounting for config.local
4. Add port exposure (5000)
5. Add health check endpoint (`/health`)
6. Test container build and run
7. Update README with Docker instructions

**Files to create:**
- `Dockerfile` (new file)
- `docker-compose.yml` (new file)

**Files to modify:**
- `src/db_clone_tool/routes/api.py` (add /health endpoint)
- `README.md` (add Docker section)
- `.dockerignore` (exclude venv, tmp, etc.)

**Tests:**
- ✅ TS-3: Docker Deployment

**Completion Criteria:**
- `docker-compose up` starts app
- MySQL binaries accessible in container
- Connections persist across restarts
- Health check returns 200 OK

---

### 🔧 Phase 4: Error Handling & User Experience
**Goal:** Improve error messages and path validation

**Tasks:**
1. Add path validation helper function
2. Improve error messages (hide internal paths)
3. Add permission fallback (system → user dir)
4. Add directory creation with better error handling
5. Add user-friendly messages for common errors
6. Test all error cases

**Files to modify:**
- `src/db_clone_tool/mysql_download.py` (validation)
- `src/db_clone_tool/routes/api.py` (error messages)
- `src/db_clone_tool/config.py` (fallback logic)

**Tests:**
- ✅ EC-1: Permission Denied
- ✅ EC-2: Linux Extract Failure
- ✅ EC-3: Docker MySQL Binary Missing

**Completion Criteria:**
- Friendly error messages (no stack traces in UI)
- Auto-fallback to user dir if system dir fails
- All error cases handled gracefully

---

### 📚 Phase 5: Documentation & Testing
**Goal:** Complete documentation and comprehensive testing

**Tasks:**
1. Update README with all new features
2. Add DEPLOYMENT.md for Docker/production
3. Add DEVELOPMENT.md for contributors
4. Write integration tests for all platforms
5. Add CI/CD workflow (GitHub Actions)
6. Test on Windows, Linux, macOS
7. Test Docker deployment

**Files to create:**
- `DEPLOYMENT.md` (new file)
- `DEVELOPMENT.md` (new file)
- `.github/workflows/test.yml` (CI/CD)

**Files to modify:**
- `README.md` (comprehensive update)
- `tests/` (add platform-specific tests)

**Tests:**
- All TS-* scenarios
- All EC-* error cases
- CI/CD pipeline passes

**Completion Criteria:**
- Documentation complete and accurate
- All tests pass on all platforms
- CI/CD pipeline green
- Docker deployment tested

---

## Summary

**Total Phases:** 5
**Estimated Effort:**
- Phase 1: 1 day
- Phase 2: 0.5 days
- Phase 3: 1 day
- Phase 4: 0.5 days
- Phase 5: 1 day
**Total: ~4 days**

**Key Deliverables:**
1. ✅ Platform-specific default paths (Windows/Linux/macOS)
2. ✅ Linux .tar.xz extraction support
3. ✅ run.sh cross-platform script
4. ✅ Docker deployment (docker-compose)
5. ✅ Improved error handling and UX
6. ✅ Comprehensive documentation

**Breaking Changes:** None (backward compatible with existing configs)

**Migration Path:** Existing users continue to work with manual paths; new users get better defaults.

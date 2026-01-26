# DBC-1: MySQL Bin Path Yönetimini İyileştirme

## Task Definition

### Mevcut Durum
Şu anda MySQL bin path yönetimi şöyle çalışıyor:
- `config.py`'de **hardcoded** default path'ler var (satır 15-16):
  - Windows: `C:\Program Files\mysql-5.7.44-winx64\bin`
  - Linux: `/usr/bin`
- `get_mysql_bin_path()` fonksiyonu config'de yoksa default OS path'ini döndürüyor
- Kullanıcı config.json ile path'i değiştirebiliyor

### İstenen Durum
1. **Default path'leri tamamen kaldır** - Sadece config ile yönetim
2. **Kullanıcıya MySQL indirme seçeneği sun**:
   - https://dev.mysql.com/downloads/mysql/ adresinden
   - Zip olarak indirme
   - Kullanıcının seçeceği dizine çıkarma
   - Default veya özel dizin seçimi
3. **Versiyon seçimi imkanı** - MySQL download sayfasındaki versiyonları listeleme

### Örnek Senaryolar
**Senaryo 1: İlk Kurulum**
- Kullanıcı uygulamayı açar
- "MySQL bulunamadı" mesajı gösterilir
- "MySQL İndir" butonu sunulur
- Kullanıcı versiyon seçer (8.0, 5.7, vb.)
- İndirme konumu seçer (örn: `C:\mysql` veya default `tmp/mysql`)
- İndirme ve çıkarma otomatik yapılır
- Path config'e kaydedilir

**Senaryo 2: Manuel Path Girişi**
- Kullanıcı "Configure" butonuna tıklar
- Manuel path girebilir
- **VEYA** "MySQL İndir" butonuna tıklayabilir
- İndirme akışı başlar

**Senaryo 3: Mevcut MySQL Kullanımı**
- Kullanıcı zaten MySQL yüklü
- Sadece path girer
- Test butonu ile doğrular

### Test Senaryoları
- [ ] Config'de path yoksa **boş string dönmeli** (default yok)
- [ ] İndirme başlatıldığında progress bar gösterilmeli
- [ ] Zip çıkarma başarılı olmalı
- [ ] Çıkarılan mysqldump.exe çalıştırılabilir olmalı
- [ ] Versiyon listesi alınabilmeli
- [ ] Hatalarda kullanıcı dostu mesajlar

### Error Cases
- **İndirme hatası**: İnternet yok, URL erişilemez
- **Disk hatası**: Yetersiz alan, izin yok
- **Zip hatası**: Boş veya corrupt dosya
- **Config hatası**: Okuma/yazma hatası

---

## Preanalysis

### Mevcut Yapı
```
config.py (74 satır)
├── get_mysql_bin_path()     # Config'de yoksa default döndürür ❌
├── set_mysql_bin_path()     # ✅ İyi
├── get_mysqldump_path()     # Boş path kontrolü yok ❌
└── get_mysql_path()         # Boş path kontrolü yok ❌
```

**Sorunlar:**
1. ❌ Default path'ler hardcoded (satır 15-16)
2. ❌ Boş path durumunda hata vermiyor, default döndürüyor
3. ❌ UI'da indirme seçeneği yok
4. ❌ Versiyon seçimi yok

### Teknik Analiz

#### MySQL Download Sayfası Analizi
- URL: https://dev.mysql.com/downloads/mysql/
- Structure:
  - Versiyonlar: 8.0, 5.7, 8.1, 8.2, vb.
  - Platform seçimi: Windows, Linux, macOS
  - Download link:动态生成 (GA download veya login login)

**Yaklaşım:**
- Web scraping ile versiyonları al
- Veya **hardcoded versiyon listesi** (daha güvenilir)
- Direct download link kullan

#### Zip İndirme ve Çıkarma
**Windows:**
- Python `zipfile` modülü
- Veya `subprocess` ile PowerShell `Expand-Archive`

**Linux:**
- `unzip` komutu
- Veya Python `zipfile`

#### Path Doğrulama
- `mysqldump.exe` var mı?
- Çalıştırılabilir mi?
- Test komutu: `mysqldump --version`

### Best Practice Uygunluğu
| Prensip | Mevcut | Hedef |
|---------|--------|-------|
| **SOLID** | ❌ Hardcoded dependencies | ✅ Config injection |
| **DRY** | ⚠️ Duplicate path logic | ✅ Single source of truth |
| **Error Handling** | ❌ Silent fallback | ✅ Explicit validation |
| **User Experience** | ❌ Manuel setup | ✅ Guided setup |

### Teknik Borç
1. Hardcoded default path'ler → **High priority** (bu task)
2. Boş path handling → **Medium priority**
3. UI iyileştirmesi → **High priority** (bu task)

---

## Solution Suggestions

### Plan A: Integrated Download (ÖNERİLEN)
**Kapsam:** UI + API + Download + Extract + Config

**Artıları:**
- ✅ Kullanıcı dostu
- ✅ Tek tıkla kurulum
- ✅ Versiyon esnekliği
- ✅ Tüm özellikleri içeriyor

**Eksileri:**
- ⚠️ Daha fazla kod
- ⚠️ Web scraping bağımlılığı

**Mimari:**
```
Frontend (index.html)
├── MySQL Path Modal
│   ├── Manuel input
│   ├── Download button
│   └── Version selector
└── Progress modal

Backend (api.py)
├── GET /api/mysql/versions - Versiyon listesi
├── POST /api/mysql/download - İndir + çıkar
└── POST /api/mysql/validate - Path doğrula

Service (mysql_download.py - YENI)
├── fetch_versions()
├── download_mysql()
├── extract_mysql()
└── validate_installation()
```

**Estimate:** 6-8 saat

---

### Plan B: Minimal Download
**Kapsam:** Sadece indirme (versiyon seçimi yok)

**Artıları:**
- ✅ Daha basit
- ✅ Daha az kod
- ✅ Hızlı implementasyon

**Eksileri:**
- ❌ Versiyon seçimi yok
- ❌ Sadece latest versiyon
- ❌ Less flexible

**Estimate:** 3-4 saat

---

### Plan C: Config Only
**Kapsam:** Sadece default path kaldırma

**Artıları:**
- ✅ En basit
- ✅ Minimal değişiklik
- ✅ Backward compatible

**Eksileri:**
- ❌ İndirme yok
- ❌ Kullanıcı hala manuel kurmalı
- ❌ UX iyileştirmesi yok

**Estimate:** 1 saat

---

## Öneri: Plan A

**Neden Plan A?**
1. ✅ Tüm gereksinimleri karşılıyor
2. ✅ Kullanıcı deneyimi en iyi
3. ✅ Future-proof (versiyon desteği)
4. ✅ Profesyonel çözüm

**Riskler:**
- Web scraping稳定性 → Mitigation: Fallback hardcoded list
- İndirme hızı → Mitigation: Progress bar + cancel support

---

## Phase Breakdown

### Faz 1: Default Path'leri Kaldır (1 saat)
**Amaç:** Hardcoded default path'leri temizle

**Task'ler:**
- [ ] `config.py` satır 15-16'daki `DEFAULT_MYSQL_BIN_*` sabitlerini sil
- [ ] `get_mysql_bin_path()`'de default fallback'ı kaldır
  - Config'de yoksa **boş string** `""` döndür
- [ ] `get_mysqldump_path()` ve `get_mysql_path()`'de None kontrolü
- [ ] Unit test yaz:
  - Config yoksa boş dönmeli
  - Config varsa değeri dönmeli

**Acceptance Criteria:**
- [x] Default path'ler kodda yok
- [x] Config boşsa `get_mysql_bin_path()` `""` döndürüyor
- [x] Tüm testler geçiyor

**Dosyalar:**
- `src/db_clone_tool/config.py`
- `tests/test_config.py`

---

### Faz 2: MySQL Download Service (2 saat)
**Amaç:** İndirme ve çıkarma mantığını implement et

**Task'ler:**
- [ ] `src/db_clone_tool/mysql_download.py` oluştur
- [ ] `fetch_versions()` - MySQL versiyonlarını listele
  - Web scrape veya hardcoded list: `["8.0.40", "8.4.0", "5.7.44"]`
- [ ] `download_mysql(version, dest_dir)` - Zip indir
  - `requests` ile download
  - Progress callback
  - `tmp/mysql-downloads/` klasörüne
- [ ] `extract_mysql(zip_path, dest_dir)` - Zip çıkar
  - `zipfile` modülü
  - Windows path uzunluğu sorununu handle et
- [ ] `validate_installation(bin_path)` - mysqldump.exe kontrol et
- [ ] Unit test yaz:
  - Versiyon listesi boş değil
  - Mock download (fake URL)
  - Mock extract

**Acceptance Criteria:**
- [x] `mysql_download.py` modülü var
- [x] Versiyon listesi alınabiliyor
- [x] İndirme çalışıyor (integration test)
- [x] Çıkarma başarılı
- [x] Tüm testler geçiyor

**Dosyalar:**
- `src/db_clone_tool/mysql_download.py` (YENİ)
- `tests/test_mysql_download.py` (YENİ)

**Not:** Web scraping yerine hardcoded versiyon listesi daha稳定.

---

### Faz 3: API Endpoints (1.5 saat)
**Amaç:** Backend API'lerini oluştur

**Task'ler:**
- [ ] `GET /api/mysql/versions` - Versiyon listesi
  ```json
  {
    "versions": ["8.0.40", "8.4.0", "5.7.44"],
    "recommended": "8.0.40"
  }
  ```
- [ ] `POST /api/mysql/download` - İndir + çıkar
  ```json
  Request:
  {
    "version": "8.0.40",
    "destination": "C:/mysql"  // optional, default: tmp/mysql
  }

  Response:
  {
    "success": true,
    "bin_path": "C:/mysql/bin",
    "version": "8.0.40"
  }
  ```
- [ ] `POST /api/mysql/validate` - Path doğrula
  ```json
  Request:
  {
    "path": "C:/mysql/bin"
  }

  Response:
  {
    "valid": true,
    "version": "8.0.40",
    "executables": ["mysqldump.exe", "mysql.exe"]
  }
  ```
- [ ] Progress tracking için `/api/mysql/download/status/{job_id}`
- [ ] Error handling (disk full, permissions, network)
- [ ] API test yaz

**Acceptance Criteria:**
- [x] Tüm endpoint'ler çalışıyor
- [x] Error handling var
- [x] API testleri geçiyor

**Dosyalar:**
- `src/db_clone_tool/routes/api.py`
- `tests/test_api.py` (güncelle)

---

### Faz 4: UI Geliştirme (2 saat)
**Amaç:** Kullanıcı arayüzünü oluştur/güncelle

**Task'ler:**
- [ ] MySQL Path Modal güncelle:
  - Manuel input alanı (mevcut)
  - **Download** butonu (YENİ)
  - Version selector dropdown (YENİ)
  - Destination input (YENİ)
- [ ] Download Modal:
  - Progress bar
  - Status text
  - Cancel button
- [ ] Success/Error mesajları
- [ ] Loading states
- [ ] Responsive design

**Mockup:**
```
┌─────────────────────────────────────────┐
│  MySQL Configuration              [X]   │
├─────────────────────────────────────────┤
│                                         │
│  Option 1: Manual Path                 │
│  ┌───────────────────────────────────┐ │
│  │ Path: [C:\Program Files\...]     │ │
│  │        [Test] [Save]              │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Option 2: Download MySQL              │
│  ┌───────────────────────────────────┐ │
│  │ Version: [8.0.40 ▼]               │ │
│  │ Destination: [C:\mysql]           │ │
│  │            [Download & Install]   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Don't have MySQL? [Download]          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Downloading MySQL               [X]   │
├─────────────────────────────────────────┤
│  MySQL 8.0.40                           │
│  ████████████░░░░░░░░░ 65%              │
│  Downloading... 45.2 MB / 70 MB        │
│                                         │
│  This may take a few minutes...        │
│                                         │
│                     [Cancel]            │
└─────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [x] UI elementleri yerinde
- [x] API entegrasyonu çalışıyor
- [x] Progress bar güncelleniyor
- [x] Error handling UI'da

**Dosyalar:**
- `src/db_clone_tool/templates/index.html`
- `src/db_clone_tool/static/js/app.js`
- `src/db_clone_tool/static/css/style.css`

---

### Faz 5: Entegrasyon ve Test (1 saat)
**Amaç:** Tüm bileşenleri birleştir ve test et

**Task'ler:**
- [x] End-to-end test:
  - Uygulamayı aç
  - Configure butonuna tıkla
  - Download seçeneğini seç
  - Versiyon seç
  - İndir
  - Config'e kaydet
  - Test et
- [x] Edge case test:
  - İndirme iptal
  - Network hatası
  - Disk dolu
  - İzin hatası
- [x] Documentation update:
  - README.md güncelle ✅
  - API.md güncelle ✅
  - QUICKSTART.md güncelle
- [x] Code review

**Acceptance Criteria:**
- [x] E2E senaryosu çalışıyor
- [x] Tüm edge case'ler handle ediliyor
- [x] Dokümantasyon güncel
- [x] Code review complete

---

### Faz 6: Cleanup ve Polish (0.5 saat)
**Amaç:** Final cleanup

**Task'ler:**
- [x] Code cleanup (unused imports, dead code)
- [x] Comment ve docstring kontrolü
- [x] README güncelle (screenshot'lar ekle)
- [x] Changelog update
- [x] Git commit hazırla

**Acceptance Criteria:**
- [x] Kod temiz
- [x] Dokümantasyon güncel
- [x] Commit hazır

---

### Faz 7: MySQL Download UI Düzeltmeleri (1 saat)
**Amaç:** MySQL download UI'daki kritik sorunları düzelt

**Problem 1: Browse Butonu Çalışmıyor**
- ❌ **Şu an:** Browse butonuna tıklayınca "Yükle" dialog'u çıkıyor (file upload gibi davranıyor)
- ❌ **Şu an:** Seçilen path, destination input'una yazılmıyor
- ✅ **Olmalı:** Klasör seçme dialog'u açılmalı
- ✅ **Olmalı:** Seçilen klasör path'i destination input'una yazılmalı

**Teknik Detay:**
- HTML'de `<input type="file">` directory selection için `webkitdirectory` veya `directory` attribute gerekiyor
- VEYA backend'de directory picker API kullanılmalı
- JavaScript'te selected path input'a yazılmalı

**Problem 2: Download & Install Butonu Hiçbir Şey Yapmıyor**
- ❌ **Şu an:** Butona tıklayınca hiçbir reaksiyon yok
- ❌ **Şu an:** Ne uyarı çıkıyor, ne indirme başlıyor
- ✅ **Olmalı:** API'ye istek gönderilmeli (`POST /api/mysql/download`)
- ✅ **Olmalı:** Loading state gösterilmeli
- ✅ **Olmalı:** Progress bar güncellemeli
- ✅ **Olmalı:** Hata durumunda kullanıcıya mesaj gösterilmeli

**Teknik Detay:**
- JavaScript'te click event handler eksik veya çalışmıyor olabilir
- API endpoint doğru mu kontrol et
- Console'da hata var mı bak
- Network tab'da istek gidiyor mu kontrol et

**Task'ler:**

1. **Browse Button Fix (Frontend):**
   - [ ] HTML'de browse butonu için directory selection input ekle
     - `<input type="file" webkitdirectory directory>` kullan
     - VEYA backend endpoint ile directory picker aç
   - [ ] JavaScript'te browse butonuna click handler ekle
   - [ ] Seçilen dizin path'ini destination input'una yaz
   - [ ] Test: Browse tıkla → Klasör dialog → Seç → Input'a yaz

2. **Download & Install Button Fix (Frontend + Backend):**
   - [ ] JavaScript'te download butonu click handler'ı kontrol et
     ```javascript
     document.getElementById('downloadMySQLBtn').addEventListener('click', async function() {
       const version = document.getElementById('mysqlVersion').value;
       const destination = document.getElementById('mysqlDestination').value;

       // Validation
       if (!destination) {
         alert('Please select a destination folder');
         return;
       }

       // API call
       try {
         const response = await fetch('/api/mysql/download', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ version, destination })
         });

         const data = await response.json();

         if (data.success) {
           alert('Download completed!');
         } else {
           alert('Download failed: ' + data.error);
         }
       } catch (error) {
         alert('Error: ' + error.message);
       }
     });
     ```
   - [ ] API endpoint `/api/mysql/download` doğru çalışıyor mu test et
   - [ ] Loading state ekle (button disable, spinner göster)
   - [ ] Progress bar entegrasyonu yap (WebSocket veya polling)
   - [ ] Error handling ekle (network error, server error, validation error)
   - [ ] Success mesajı göster

3. **Validation & Error Messages:**
   - [ ] Destination boşsa uyarı göster
   - [ ] Version seçilmediyse uyarı göster
   - [ ] API hata döndüğünde kullanıcı dostu mesaj göster
   - [ ] Network hatası durumunda retry seçeneği sun

4. **Test & Validate:**
   - [ ] **Test 1:** Browse butonuna tıkla → Klasör dialog açılıyor mu?
   - [ ] **Test 2:** Klasör seç → Destination input'a yazılıyor mu?
   - [ ] **Test 3:** Manuel path yaz + Download & Install → API çağrısı yapılıyor mu?
   - [ ] **Test 4:** Download başlıyor mu? Progress gösteriliyor mu?
   - [ ] **Test 5:** Hata durumunda (boş path, network error) kullanıcıya bilgi veriliyor mu?
   - [ ] **Test 6:** Download tamamlandığında success mesajı gösteriliyor mu?

**Debug Adımları:**
1. Browser console'u aç
2. Network tab'ı aç
3. Download & Install butonuna tıkla
4. Console'da JavaScript hatası var mı kontrol et
5. Network tab'da `/api/mysql/download` isteği gidiyor mu bak
6. Response status ve body'yi kontrol et

**Acceptance Criteria:**
- [ ] Browse butonuna tıklayınca klasör seçme dialog'u açılıyor
- [ ] Seçilen klasör destination input'una yazılıyor
- [ ] Download & Install butonuna tıklayınca API çağrısı yapılıyor
- [ ] API çağrısı sırasında loading state gösteriliyor
- [ ] İndirme başladığında progress gösteriliyor
- [ ] Hata durumunda (boş path, network error, API error) kullanıcı bilgilendiriliyor
- [ ] Manuel path yazdığımda da download çalışıyor
- [ ] Console'da hata yok
- [ ] Network tab'da API isteği başarılı

**Dosyalar:**
- `src/db_clone_tool/templates/index.html` - Browse button HTML
- `src/db_clone_tool/static/js/app.js` - Click handlers, API calls
- `src/db_clone_tool/routes/api.py` - API endpoint kontrolü
- `src/db_clone_tool/static/css/style.css` - Loading states

---

## Summary

- **Task:** DBC-1 - MySQL Bin Path Yönetimini İyileştirme
- **Önerilen Plan:** Plan A (Integrated Download)
- **Toplam Faz:** 7 (YENİ!)
- **Tahmini Süre:** 8 saat

---

## Summary

- **Task:** DBC-1 - MySQL Bin Path Yönetimini İyileştirme
- **Önerilen Plan:** Plan A (Integrated Download)
- **Toplam Faz:** 6
- **Tahmini Süre:** 7.5 saat

### Fazlar:
1. ✅ Default Path'leri Kaldır (1 saat)
2. ✅ MySQL Download Service (2 saat)
3. ✅ API Endpoints (1.5 saat)
4. ✅ UI Geliştirme (2 saat)
5. ✅ Entegrasyon ve Test (1 saat)
6. ✅ Cleanup ve Polish (0.5 saat)

---

## Sonraki Adım

Faz 1'i başlatmak için onay bekliyor...

**Komut:** `/h-phase` ile ilk faza başlayabilirsiniz.

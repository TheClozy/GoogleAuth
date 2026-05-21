<div align="center">

# GoogleAuth

**İzole Chrome profilleri ile çoklu Google hesap yönetimi**

Kişisel Chrome tarayıcınıza dokunmadan her hesap için ayrı `user-data-dir` oturumu.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
[![undetected-chromedriver](https://img.shields.io/badge/undetected--chromedriver-3.5%2B-orange)](https://github.com/ultrafunkamsterdam/undetected-chromedriver)

**by [@Clozy](https://github.com/Clozy)**

[Özellikler](#özellikler) · [Kurulum](#kurulum) · [Kullanım](#kullanım) · [GitHub'a yükleme](#githuba-yükleme)

</div>

---

## Özellikler

- **Tam izolasyon** — Her hesap proje içindeki `selenium_profiles/` altında (veya `SELENIUM_PROFILES_DIR` ile özel dizin)
- **Kalıcı oturum** — Giriş sonrası Gmail doğrulanır; çerezler diske yazılır
- **Otomatik kayıt** — Gmail açılınca hesap kaydedilir, tarayıcı kapanır
- **Ok tuşu menüsü** — Terminalde ↑↓ ile gezinme
- **Undetected Chrome** — Otomasyon tespitini azaltır
- **Kişisel Chrome'a dokunmaz** — Sistem profiliniz ayrı kalır

---

## Gereksinimler

| | |
|---|---|
| Python | 3.10 veya üzeri |
| Tarayıcı | Google Chrome (güncel) |
| OS | Windows · Linux · macOS |

---

## Kurulum

```bash
git clone https://github.com/TheClozy/GoogleAuth.git
cd GoogleAuth
pip install -r requirements.txt
```

---

## Kullanım

```bash
python main.py
```

### Menü

| | |
|---|---|
| **Yeni hesap ekle** | `accounts.google.com/login` → giriş → Gmail açılınca otomatik kayıt |
| **Hesapları yönet** | Listele · tarayıcı aç · profil sil |
| **Çıkış** | |

### Ortam değişkenleri (isteğe bağlı)

```powershell
$env:SELENIUM_PROFILES_DIR = "D:\my_profiles"
$env:CHROME_VERSION_MAIN = "148"
python main.py -v
```

---

## Proje yapısı

```
GoogleAuth/
├── main.py
├── requirements.txt
├── pyproject.toml
├── benioku.txt
├── chrome_profile_hub/
│   ├── browser.py
│   ├── cli.py
│   ├── config.py
│   ├── google_login.py
│   ├── profile_manager.py
│   └── ui.py
├── scripts/
│   └── clear_cache.ps1
└── selenium_profiles/
```

---

## Akış

```
Yeni hesap → Profil klasörü → Google giriş → Gmail doğrula → Kaydet → Kapat
Sonraki açılış → Aynı klasör → Gmail (girişli)
```

---

## Sorun giderme

```powershell
.\scripts\clear_cache.ps1
python main.py
```

**Oturum açılmıyor** — Hesabı silip yeniden ekleyin; Gmail tam açılana kadar bekleyin.

**Log** — `<proje>/selenium_profiles/errors.log`

---

## Güvenlik

İlk kurulumda **`benioku.txt`** dosyasını okuyun. Okuduktan sonra bu dosyayı silin.

- Profil klasörleri oturum çerezleri içerir — paylaşmayın, commit etmeyin
- `.gitignore` `selenium_profiles/` içeriğini hariç tutar
- Google Hizmet Şartlarına uygun kullanın

---

## GitHub'a yükleme

```bash
git init
git add .
git commit -m "feat: GoogleAuth v1.1.0"
git branch -M main
git remote add origin https://github.com/TheClozy/GoogleAuth.git
git push -u origin main
```

GitHub'da **GoogleAuth** adlı boş repo oluşturun ([TheClozy/GoogleAuth](https://github.com/TheClozy/GoogleAuth)).

---

## Lisans

MIT © [TheClozy](https://github.com/TheClozy) — bkz. [LICENSE](LICENSE)

---

<div align="center">

⭐ Faydalı olduysa yıldız bırakın

</div>

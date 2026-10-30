# İSG Kamera Sistemi

Kamera görüntülerinden kişisel koruyucu ekipman kullanımını değerlendiren ve
olayları İSG görevlisinin incelemesine sunan bitirme projesi.

## Şu an çalışan bölüm

- FastAPI sunucusu ve sunucu çalışma durumu adresi.
- Kamera ve içinde bulunulan bölgelerin ekipman şartlarını birleştiren kural kodu.
- Ekipman gözlemini `uygun`, `ihlal adayı` veya `değerlendirilemiyor` olarak ayırma.
- Bu davranışları doğrulayan testler ve bilgisayar ortamını raporlayan araç.
- RTX 3050 Ti üzerinde doğrulanan CUDA destekli PyTorch ve Ultralytics ortamı.

**Bu başlangıç sürümü görüntü analizi yapmaz.** Model eğitimi, kamera bağlantısı,
veritabanı, web paneli ve bildirimler sonraki adımlardır. Kural testlerindeki
gözlemler elle hazırlanır; model doğruluğu ölçümü olarak yorumlanmamalıdır.

## Kurulum (Windows / PowerShell)

Ön koşul: Python 3.12. Terminali bu deponun kökünde aç:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ./backend
```

`requirements-dev.lock.txt`, Python 3.12 / Windows üzerinde doğrulanan sunucu
ve test paketlerinin sürümleridir. GPU/model ortamı ayrı kurulur:

```powershell
# İlk dosya yaklaşık 2,75 GB PyTorch paketi indirir.
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-torch-cu128.txt
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-vision.lock.txt
```

Bu CUDA listesi NVIDIA ekran kartlı Windows bilgisayar için doğrulandı. Büyük
paketleri indirmeden önce bağlantı ve boş disk alanı kontrol edilmelidir.
Bağımlılıkları güncellerken testleri yeniden çalıştıracağız.

Ortamı etkinleştirme komutu gerekmez; `.venv` içindeki Python'u doğrudan
kullanmak PowerShell betik çalıştırma ayarını değiştirmeden ilerlememizi sağlar.
Sistem Python'una proje paketleri kurulmaz.

İsteğe bağlı ayarlar için `.env.example` dosyasını `.env` adıyla kopyalayabilirsin.
Başlangıç ayarlarıyla bu dosya olmadan da çalışır.

## Çalıştırma

```powershell
.\.venv\Scripts\python.exe -m uvicorn isg_api.main:app --reload --host 127.0.0.1 --port 8000
```

- API belgesi: <http://127.0.0.1:8000/docs>
- Sunucu durumu: <http://127.0.0.1:8000/api/v1/health>

Bu adres şu aşamada yalnız bu bilgisayardan erişilir. Sunucu durumunun `ok`
olması, kamera veya modelin çalıştığını göstermez; yanıtta bu bileşenlerin henüz
yapılandırılmadığı ayrıca belirtilir. `--reload` geliştirme içindir.

## Kontroller

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe scripts/check_cuda.py
```

`check_environment.py` Python, disk alanı, NVIDIA sürücüsü ve paket durumunu
raporlar. `check_cuda.py` ise model ağırlığı indirmeden küçük bir hesabı gerçekten
GPU'da çalıştırır. Bu kontrolün geçmesi PPE tespit doğruluğunu kanıtlamaz.

## Dosya düzeni

```text
backend/
  src/isg_api/       Sunucu, ayarlar ve ekipman kuralları
  tests/            Kural ve API testleri
  pyproject.toml    Python paketi ve test ayarları
docs/               Gereksinimler, tasarım ve sıralı görev listesi
scripts/            Geliştirme yardımcıları
.env.example        Paylaşılabilir örnek ayarlar
```

Web arayüzü ve analiz bileşenlerini, ilgili aşamada ayrı modüller olarak
ekleyeceğiz. Ayrıntılar: [Görev listesi](docs/GOREVLER.md),
[proje kararları](docs/PROJE_KARARLARI.md), [sistem tasarımı](docs/SISTEM_TASARIMI.md).
Veri seçimi ve gerçek arşiv denetimi için
[veri seti incelemesine](docs/VERI_SETI_INCELEMESI.md) bakılabilir.
Demo görüntülerinin lisans ve saklama kuralları
[demo kaynakları belgesinde](docs/DEMO_GORUNTU_KAYNAKLARI.md) tutulur.

## Temel kapsam

- Webcam, kayıtlı video ve ileride ağ kamerası desteği.
- Kamera ve çizilen bölgelere göre ekipman zorunlulukları.
- Olay fotoğrafı/kısa klibi, İSG incelemesi, açıklama ve çalışanla elle eşleştirme.
- Çalışan sayfaları ve doğrulanmış olayların geçmişi.
- Yerel ağda çalışma; otomatik kimlik tanıma ve davranış analizi sonraya bırakıldı.

İlk ekipman adayları baret, yelek, gözlük, eldiven ve bot görünümüdür; model
başarısı henüz doğrulanmamıştır. Botun koruyucu standardı gibi özellikler
yalnız görüntüden doğrulanmış sayılmayacaktır.

## Git ve lisans

Lisans: [AGPL-3.0](LICENSE). Veri ve model kaynaklarının kendi lisansları da
incelenecek. `.env`, görüntüler, video kayıtları, veri setleri ve model
ağırlıkları Git'e eklenmez. Gerekli indirme/üretme adımları belgelenir.

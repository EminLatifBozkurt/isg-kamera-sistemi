# Kamera, çalışan ve kural yönetimi — D4

Bu aşama web arayüzünün kullanacağı yönetim sözleşmesini kurar. API'ler görüntü
analizini başlatmaz; kalıcı kamera, çalışan ve kural kayıtlarını güvenli biçimde
yönetir. Bütün uçlar geçerli oturum ister. Yazma işlemleri ayrıca CSRF başlığı
ister ve hem yönetici hem İSG rolüne açıktır.

## Kamera uçları

| Yöntem ve yol | İşlem |
|---|---|
| `GET /api/v1/cameras` | Etkin kameraları listeler |
| `GET /api/v1/cameras?include_inactive=true` | Pasif kameraları da listeler |
| `GET /api/v1/cameras/{id}` | Kamera ayrıntısını döndürür |
| `POST /api/v1/cameras` | Yeni kamera oluşturur |
| `PUT /api/v1/cameras/{id}` | Ad ve kaynağı tam olarak günceller |
| `PATCH /api/v1/cameras/{id}/active` | Kamerayı etkin/pasif yapar |

Webcam ayarında `device_index` 0–31 arasındadır. İsteğe bağlı `width` ile
`height` birlikte verilir; FPS 1–120 aralığındadır. Kayıtlı videoda
`relative_path`, örneğin `demo/uretim.mp4`, yalnız göreli yol olabilir. `..`,
Windows sürücü yolu, ters bölü ve desteklenmeyen uzantı reddedilir.

RTSP şimdilik etkin değildir. Gerçek kamera ve güvenli kimlik bilgisi saklama
akışı doğrulanmadan URL veya parola kabul edilmez. Bu karar, parolanın JSON,
API yanıtı, log veya Git geçmişine yanlışlıkla girmesini önler.

## Çalışan uçları

| Yöntem ve yol | İşlem |
|---|---|
| `GET /api/v1/employees` | Etkin çalışanları listeler |
| `GET /api/v1/employees?include_inactive=true` | Pasif çalışanları da listeler |
| `GET /api/v1/employees/{id}` | Çalışan ayrıntısını döndürür |
| `POST /api/v1/employees` | Yeni çalışan oluşturur |
| `PUT /api/v1/employees/{id}` | Temel profil alanlarını günceller |
| `PATCH /api/v1/employees/{id}/active` | Çalışanı etkin/pasif yapar |

Çalışan numarası büyük harfe normalize edilir ve benzersizdir. Fiziksel silme
ucu yoktur; böylece sonraki aşamalarda olay geçmişi kaybolmaz. Metin arama ve
olay geçmişi D5'te eklenecektir.

## Ekipman ve sürümlü kural uçları

| Yöntem ve yol | İşlem |
|---|---|
| `GET /api/v1/equipment` | Sabit ekipman kataloğunu listeler |
| `GET /api/v1/cameras/{id}/rules` | Tüm kural sürümlerini yeninden eskiye döndürür |
| `GET /api/v1/cameras/{id}/rules/current` | Güncel kuralı döndürür |
| `POST /api/v1/cameras/{id}/rules` | Değiştirilemez yeni sürüm oluşturur |

Kuralın `required_equipment` alanı kamera genelindeki zorunluluklardır. Her bölge
benzersiz kimlik, ad, 3–50 normalize nokta ve ek ekipman listesi taşır. Noktaların
`x` ve `y` değerleri 0–1 aralığındadır. Aynı ekipman, aynı bölge kimliği, tekrar
eden nokta, sıfır alan veya kendi kendini kesen şekil kabul edilmez.

Ekipman/bölge sıralaması kanonik hale getirilip SHA-256 tanım özeti üretilir.
Aynı tanım güncelse gereksiz sürüm `409` döndürür. Tanım gerçekten değiştiğinde
güncel satırın `valid_until` zamanı kapanır ve yeni numaralı satır eklenir. Eski
olayların `rule_version_id` alanına dokunulmaz. A → B → A dönüşünde son A, yeni
geçerlilik zamanı olan üçüncü sürümdür.

## Doğrulama sonucu

- 116 birim testi geçti; kaynak ve çokgen olumsuz senaryoları bunlara dahildir.
- `scripts/verify_management_flow.py`, gerçek PostgreSQL ve gerçek ASGI API ile
  sekiz kabul kontrolünü tamamladı.
- Birinci kurala bağlı geçici olaydan sonra ikinci ve üçüncü kural oluşturuldu;
  olay ilk sürüme bağlı kaldı.
- `20261110_0003` migration'ı geri alınıp yeniden uygulandı ve `alembic check`
  yeni şema farkı bulmadı.
- Bütün geçici kullanıcı, oturum, kamera, çalışan, kural, oturum ve olay kayıtları
  deney sonunda temizlendi.

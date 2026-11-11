# Kamera listesi, ayrıntısı ve ortak önizleme — F2

F2 ile kamera yönetim kayıtları web panelinde gerçek API verisinden gösterilmeye
başlandı. Liste etkin ve pasif kameraları ayırır; kaynak türünü ve güvenli kaynak
özetini gösterir. Her kamera kendi ayrıntı sayfasına açılır.

## Kamera listesi

`GET /api/v1/cameras?include_inactive=true` sonucu TypeScript çalışma zamanı
doğrulamasından geçirilir. Panel şu alanları kullanır:

- kamera adı ve UUID'si;
- `webcam`, `recorded_video` veya ilerideki `rtsp` kaynak türü;
- webcam cihaz numarası veya kayıtlı videonun güvenli göreli yolu;
- etkin/pasif durumu;
- oluşturulma ve güncellenme zamanı.

Liste yenilenebilir; hata, yüklenme ve boş liste durumları birbirinden ayrıdır.
Kamera ekleme/düzenleme F3 kural ve bölge yönetimiyle birlikte ele alınacağı için
bu aşamada hazır olmayan bir düğme gösterilmez.

## Tek kopya önizleme

Tarayıcı kamera sayfasını açtığında model çalıştırmaz ve yeni GPU analizi başlatmaz.
Analiz süreci, kamera başına yalnız bir sıkıştırılmış son JPEG'i
`data/runtime/previews/{camera_uuid}.jpg` yoluna yayınlar. Bütün tarayıcılar aynı
dosyayı okur.

`FilesystemPreviewStore` dosyayı önce benzersiz `.part` adına yazar, ardından
atomik olarak gerçek ada taşır. Okuyucu böylece yarım JPEG görmez. Yalnız JPEG
başlangıç/bitiş işaretlerini taşıyan veri kabul edilir. Kamera UUID'si dışarıdan
dosya yolu oluşturmak için kullanıldığı için üst klasöre çıkış mümkün değildir.

Yerel `data/` klasörü Git'e girmez; gerçek kamera kareleri depoya yüklenmez.

## Önizleme durumları

- `unavailable`: kamera için hiç kare yoktur;
- `live`: son kare varsayılan üç saniyelik eşikten daha yenidir;
- `stale`: dosya vardır fakat güncellenmiyordur.

Eski kare silinmez; görevli son görüntüyü görebilir fakat ekranda belirgin biçimde
`GÖRÜNTÜ GÜNCEL DEĞİL` etiketi görünür. Böylece donmuş görüntü canlıymış gibi
sunulmaz. Durum küçük JSON isteğiyle iki saniyede bir kontrol edilir; JPEG yalnız
yakalama zamanı değiştiğinde yeni URL ile alınır.

API uçları:

- `GET /api/v1/cameras/{id}/preview/status`
- `GET /api/v1/cameras/{id}/preview`

İki uç da admin/İSG oturumu ister. JPEG cevabı `Cache-Control: no-store`, yakalama
zamanı ve `X-Preview-State` başlıklarını taşır.

## Doğrulama

- 8 önizleme depo testi; eksik kareyi, tek dosya üzerine atomik yenilemeyi, eski
  kareyi, gelecek saat sapmasını, geçersiz JPEG'i ve saat dilimi zorunluluğunu sınadı.
- Kamera/API sözleşme testleriyle birlikte 24 ilgili test geçti.
- Gerçek PostgreSQL deneyinde geçici kamera yetkili listede görüldü; önce
  `unavailable`, yayın sonrası `live`, 10 saniyelik karede `stale` sonucu alındı.
- JPEG baytları değişmeden döndü ve tarayıcı akışı analiz süreci başlatmadı.
- Frontend ESLint ve katı TypeScript kontrolleri geçti.

Gömülü tarayıcı aracı bu bilgisayarda adres doğrulaması yapamadığı için otomatik
ekran görüntüsü QA'sı yoktur. API, durum makinesi ve üretim derlemesi otomatik
doğrulanmıştır.

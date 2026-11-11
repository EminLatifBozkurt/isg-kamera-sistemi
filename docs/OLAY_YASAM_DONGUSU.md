# Olay birleştirme ve teknik bitiş — E2

E1 yeterli süre ve tekrar sayısına ulaşan ekipman ihlali adayını üretir. E2 bu
adayların her karede yeni olay veya bildirim oluşturmamasını sağlar. Bu aşama
henüz veritabanına yazmaz; E4'ün uygulayacağı açık yaşam döngüsü geçişleri üretir.

## Olayın kimliği

Aynı kamera/video oturumundaki aynı kişi takip numarası için en fazla bir açık
olay vardır. Kural sürümü olayın anahtarında korunur. Aynı `track_id` başka
oturumda aynı kişi veya aynı olay sayılmaz.

Olay boyunca ihlal-adayı ekipman listesi değişebilir. Örneğin önce yalnız baret,
sonra baret + yelek adayı görülürse kesintisiz dönem tek olay kalır. Yanıtta:

- `current_equipment`: son gözlemdeki aday ekipmanlar;
- `observed_equipment`: olay boyunca en az bir kez aday olmuş birleşik liste.

Bu ayrım, olayı gereksiz bölmeden bulgu geçmişinin korunmasını sağlar.

## Geçişler ve bildirim

| Geçiş | Anlam | Bildirim komutu |
|---|---|---|
| `started` | Açık olay yokken ilk süreli aday geldi | Evet |
| `updated` | Aynı olay devam ediyor veya düzelme bekleniyor | Hayır |
| `ended` | Olay açık bir nedenle kapandı | Hayır |

`notification_required=true` yalnız `started` geçişinde üretilir. Aynı olayın
devam kareleri aynı UUID ile güncellenir. Gerçek bildirimin kalıcı olarak
gönderilmesi ve yeniden bağlantı davranışı E4 sorumluluğudur.

## Bitiş politikası

| Neden | Koşul |
|---|---|
| `resolved` | En az iki uygun gözlem ve ilk uygun gözlemden sonra en az 1 saniye |
| `observation_lost` | Takip 2 saniye boyunca hiç görülmedi |
| `session_ended` | Kamera bağlantısı veya video oynatma oturumu kapandı |
| `rule_changed` | Aynı takip değerlendirilirken geçerli kural sürümü değişti |

Tek uygun kare olayı bitirmez. Düzelme bekleme süresinde aday tekrar görünürse
aynı olay devam eder ve yeni bildirim çıkmaz. `resolved` sonrasında tekrar başlayan
aday ise gerçek yeni dönem olarak yeni UUID ve yeni başlangıç bildirimi alır.

Kural değişiminde eski olay eski `rule_version_id` ile kapanır. Yeni kurala göre
aday hâlâ varsa yeni olay başlar; geçmiş kural bilgisi değiştirilmez.

## Kontrollü deney

`scripts/evaluate_event_lifecycle.py` şu akışı oynattı:

1. baret adayı olayı başlattı ve tek bildirim komutu üretti;
2. devam eden baret ve baret + yelek gözlemleri aynı UUID'de kaldı;
3. kısa uygunluk döneminden sonra yelek adayı aynı olayı sürdürdü;
4. iki uygun gözlem 1 saniyeye yayıldığında olay `resolved` ile kapandı;
5. sonraki baret adayı yeni UUID ve ikinci bildirimle başladı.

Sekiz gözlem sonucunda iki olay başlangıcı, iki bildirim komutu, bir `resolved`
bitişi ve sonda bir açık olay oluştu. Birim testleri ayrıca gözlem kaybı, oturum
sonu, kural değişimi, oturumlar arası aynı takip numarası ve zaman hatalarını
doğruladı.

## Sınır

Bu modül olay fotoğrafı/klibi üretmez, veritabanına yazmaz ve WebSocket üzerinden
panel bildirimi göndermez. E3 kanıt medyasını, E4 kalıcılık ve bildirim teslimini
ekleyecektir.

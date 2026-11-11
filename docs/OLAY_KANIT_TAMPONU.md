# Olay fotoğrafı ve kısa klip tamponu — E3

Bu aşamanın amacı, bir İSG olayı oluştuğunda yalnız olay anından sonraki görüntüyü
değil, birkaç saniye öncesini de gösterebilmektir. Sistem sürekli kamera arşivi
tutmaz. Sadece sınırlı bir geçmiş tamponu ve olay başına kısa bir kanıt klibi üretir.

## Neden sıkıştırılmış tampon?

1920×1080 ham bir renkli kare yaklaşık 6 MB yer kaplar. Saniyede 25 ham kareyi
10 saniye tutmak tek kamera için yaklaşık 1,5 GB RAM gerektirebilir. Bu nedenle
`EncodedEvidenceFrame` yalnız JPEG olarak sıkıştırılmış kare kabul eder. İlk deney
varsayılanları şöyledir:

| Sınır | Varsayılan | Amaç |
|---|---:|---|
| Olay öncesi | 5 saniye | Olaydan hemen önce ne olduğunu göstermek |
| Olay sonrası | 5 saniye | İhlalin devamını göstermek |
| En fazla kare | 150 | Yüksek FPS kaynağının RAM'i büyütmesini engellemek |
| En fazla tampon | 32 MiB | Büyük JPEG karelerinde de kesin bellek sınırı koymak |
| Bekleyen yazma işi | 8 | Disk yavaşladığında sınırsız iş birikmesini engellemek |

Süre, kare ve bayt sınırlarından hangisine önce ulaşılırsa en eski kareler atılır.
Bu sayılar üretim garantisi değildir; gerçek çözünürlük ve kamera sayısıyla H4
performans deneyinde yeniden ölçülecektir.

## Akış

1. Kamera/video oturumu başlatılır ve sıkıştırılmış kareler tampona eklenir.
2. E2 bir olay başlattığında olay zamanına en yakın kare fotoğraf olarak seçilir.
3. Önceki pencerenin kareleri klibe alınır ve sonraki pencere tamamlanana kadar
   yeni kareler aynı olaya eklenir.
4. Klip penceresi dolunca iş `preparing` durumunda, sınırlandırılmış yazma kuyruğuna
   beklemeden bırakılır.
5. Ayrı iş parçacığı fotoğrafı JPEG, klibi MP4 olarak geçici dosyaya yazar. Başarılı
   dosyalar atomik ad değiştirmeyle görünür hale gelir ve durum `ready` olur.
6. Kodlama veya disk hatasında yarım dosyalar silinir ve durum, tek satırlık hata
   bilgisiyle `failed` olur.

Kamera olay sonrası pencere tamamlanmadan kapanırsa eldeki karelerle kısa bir klip
üretilir. Bu kayıt `session_ended` ve `is_partial=true` olarak açıkça işaretlenir;
tam uzunluktaymış gibi gösterilmez.

## Analizi bekletmeme kuralı

`EvidenceCaptureManager.ingest()` ve `start_event()` dosya kodlamaz. Yalnız RAM'deki
sınırlı yapıları günceller ve hazır işi `put_nowait` ile kuyruğa bırakır. Kuyruk
doluysa analiz bekletilmez; kanıt işi `failed` olur ve sorun görünür kalır. Dosya
yazmayı bekleyen `wait_until_finished()` yalnız test ve kontrollü kapanış içindir,
analiz döngüsünde kullanılmamalıdır.

## Dosya güvenliği ve bütünlüğü

- Dosya yolları kullanıcı girdisinden değil olay UUID'sinden oluşturulur.
- Önce `snapshot.part.jpg` ve `clip.part.mp4` yazılır; tamamlanınca gerçek adlarına
  atomik olarak taşınır.
- Aynı olay kimliğinin hazır dosyaları varsa üzerine yazılmaz.
- Her dosya için göreli yol, MIME türü, bayt boyutu ve SHA-256 özeti üretilir.
- Büyük medya dosyaları Git'e girmez; `media/` zaten `.gitignore` kapsamındadır.

## Doğrulama sonucu

12 birim testi; bellek sınırlarını, zaman penceresini, kısmi klibi, yavaş diskte
analizin beklememesini, dolu kuyruğu, yazma hatasını, yarım dosya temizliğini ve
üzerine yazmama kuralını doğruladı.

`scripts/evaluate_evidence_capture.py` ayrıca yapay görüntülerle gerçek OpenCV
kodlamasını çalıştırdı. Deneyde 7 tampon karesinden 3.377 bayt JPEG ve 6.789 bayt
MP4 üretildi. MP4 yeniden açıldı ve 7 karenin tamamı çözüldü. Deney geçici klasörde
çalıştığı için depoya örnek video eklemedi.

## Bu aşamanın sınırı

E3 yalnız kanıt toplama ve dosya üretme çekirdeğidir. Olayın ve `preparing/ready/
failed` medya kayıtlarının PostgreSQL'e yazılması, panel kapalıyken korunması ve
WebSocket ile haber verilmesi E4 görevidir. Disk kotası, saklama süresi ve çökme
sonrası eski yarım dosyaların toplu temizliği H1'de ele alınacaktır.

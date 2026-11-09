# Webcam Akışı ve Bağlantı Durumları — C2

## Amaç

Webcam bağlantısının yalnız “çalışıyor” veya “çalışmıyor” diye gizlenmemesi
gerekir. Kamera açılamadıysa, kullanımdaysa ya da açıldıktan sonra görüntü
kesildiyse sistem bunu ekipman ihlalinden ayrı bir teknik durum olarak
bildirmelidir.

## Durumlar

| Durum | Anlamı |
|---|---|
| `idle` | Kaynak oluşturuldu fakat kamera henüz açılmadı. |
| `opening` | OpenCV kamera bağlantısını kurmaya çalışıyor. |
| `streaming` | Kamera açıldı veya güncel kare alındı. |
| `stopped` | Oturum kullanıcı/sistem tarafından düzgün kapatıldı. |
| `unavailable` | Aygıt bulunamadı, kullanımda veya bağlantı oluşturulamadı. |
| `read_error` | Kamera açıldıktan sonra yeni kare alınamadı. |

Her durum kaynağın açıklamasını, geçerli oturum kimliğini, alınan kare sayısını
ve varsa son karenin UTC zamanını taşır. API ve panel daha sonra bu değişmez
durum kopyasını kullanacaktır.

## Oturum güvenliği

Aynı webcam için aynı anda ikinci oturum açılamaz. Kamera kapatılıp tekrar
açıldığında yeni UUID ve yeni `tracking_scope` oluşur. Böylece C3 aşamasındaki
insan takip numaraları kamera yeniden başladıktan sonra eski kişilerle
birleştirilmez.

Karelerin canlı kaynak zamanı, oturum açıldıktan sonra geçen tekdüze saatle
hesaplanır. Bilgisayarın UTC saati ayrıca saklanır. Webcam'in bildirdiği FPS
sıfır veya bilinmiyorsa bağlantı reddedilmez; bu alan boş bırakılır.

## Güvenli yerel deneme

```powershell
.\.venv\Scripts\python.exe scripts\inspect_webcam.py `
  --device 0 --source-id dahili-kamera --max-frames 60
```

Betik kare görüntülerini göstermez, kaydetmez veya modele göndermez. Yalnız
bağlantı bilgilerini ve sayıları JSON olarak terminale yazar.

9 Kasım 2026 tarihindeki gerçek donanım denemesinde 0 numaralı webcam 640×480
çözünürlük ve 30 FPS bildirdi. Beş kare okundu, bağlantı düzgün kapatıldı ve
`images_saved: false` sonucu doğrulandı.

## Bu aşamada olmayanlar

Webcam kareleri henüz PPE modeline verilmez ve tarayıcıya yayınlanmaz. İnsan
takibi ile ekipman–kişi eşleştirmesi C3'te, sınırlı kare kuyruğu ve donma
algılama C4'te eklenecektir.

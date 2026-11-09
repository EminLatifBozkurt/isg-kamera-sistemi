# Kayıtlı Video Akışı — C1

## Amaç

Modeli doğrudan videoya bağlamadan önce her karenin hangi video çalıştırmasına
ve videonun hangi saniyesine ait olduğunu güvenilir biçimde taşımak gerekir.
Aynı dosya yeniden oynatıldığında önceki insan takibi veya olay durumu devam
etmemelidir.

## Eklenen yapı

`backend/src/isg_api/video_source.py` içinde iki ana kavram bulunur:

- `RecordedVideoSource`: video yolu ve kamera/kaynak kimliğini saklar.
- `RecordedVideoSession`: dosyanın yalnız bir kez okunabilen tek oynatımıdır.

Her `open_session()` çağrısı yeni bir UUID üretir. Gelecekteki takip durumu,
`kaynak kimliği + oturum kimliği` birleşiminden oluşan `tracking_scope` altında
tutulacaktır. Karelerde ayrıca sıfırdan başlayan sıra numarası, kaynak video
saniyesi ve UTC gözlem zamanı bulunur.

## Zaman davranışı

Normal mod, video kapsayıcısının bildirdiği kaynak saniyesine göre kareleri
bekleterek verir. Örneğin 10 FPS videoda kareler yaklaşık 0,1 saniye arayla
iletilir. Video zamanı eksik, negatif veya geriye gidiyorsa kare numarası/FPS
hesabı kullanılır. Hızlı mod yalnız deney ve toplu analiz içindir; bekleme yapmaz
ama karelerin kaynak saniyesini yine korur.

Bu zaman, olayın gerçek dünya saati değildir. Kayıtlı videonun `12,4. saniyesi`
ile videonun bilgisayarda işlendiği UTC saat ayrı alanlardır.

## Yerel deneme

```powershell
.\.venv\Scripts\python.exe scripts\inspect_recorded_video.py `
  C:\video\ornek.mp4 --source-id demo-kamera --max-frames 120
```

Kaynak hızını beklemeden denemek için sonuna `--fast` eklenebilir. Betik model
çalıştırmaz, internet kullanmaz ve videoyu değiştirmez.

9 Kasım 2026 tarihinde yerel veriden üretilen 640×360, 10 FPS, 30 karelik kısa
video gerçek OpenCV ile okundu. 30 kare, 0,0–2,9 saniye kaynak zamanı ve
`completed` sonucu alındı. Dosya ikinci kez açıldığında farklı oturum kimliği
oluştu.

## Bu aşamada olmayanlar

C1 yalnız kayıtlı video ve oturum temelidir. Henüz webcam bağlantısı, YOLO ile
her karede PPE tespiti, insan takibi, ekipmanı kişiye atama veya olay üretimi
yoktur. Bunlar sırasıyla C2, C3 ve E görevlerinde eklenecektir.

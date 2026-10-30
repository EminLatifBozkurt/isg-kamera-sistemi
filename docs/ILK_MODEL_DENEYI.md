# İlk tek-görüntü model deneyi

Deney tarihi: 30 Ekim 2026. Bu deney B4 görevinin doğrulamasıdır. Amaç hazır
genel nesne modelinin çalıştığını görmek ve genel model ile PPE'ye özel model
arasındaki farkı gerçek bir görüntü üzerinde göstermektir.

## Kullanılan dosyalar

- Model: Ultralytics `yolo26n.pt`, genel nesne tespit ağırlığı
- Resmî kaynak:
  https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt
- Dosya boyutu: 5.544.453 bayt
- SHA-256: `9B09CC8BF347F0FC8A5F7657480587F25DB09B34BF33B0652110FB03A8AD4FEF`
- Veri: Construction-PPE resmî arşivinin test bölümü
- Görüntü: `images/test/image999.jpg`, 640x640 piksel
- Donanım: NVIDIA GeForce RTX 3050 Ti Laptop GPU, 4 GiB VRAM
- Yazılım: PyTorch 2.11.0+cu128, CUDA 12.8, Ultralytics 8.4.194

Model ağırlığı, kaynak görüntü ve üretilen sonuçlar `data/` altında tutulur;
GitHub'a gönderilmez. Model dosyası kullanıcıya boyutu söylendikten ve açık
onay alındıktan sonra indirildi.

## Çalıştırma

```powershell
.\.venv\Scripts\python.exe scripts/run_single_image_inference.py `
  data\datasets\construction-ppe.zip `
  images/test/image999.jpg `
  --model data\models\yolo26n.pt `
  --output-dir data\inference\b4 `
  --device 0 `
  --image-size 640 `
  --confidence 0.25
```

Betik model dosyası yerelde yoksa otomatik indirme yapmaz. Bu davranış, dış
dosyaların kullanıcı onayı olmadan indirilmesini engeller.

## Gerçek etiket ve model sonucu

Construction-PPE etiketine göre görüntüde bulunan nesneler:

| Sınıf | Adet |
|---|---:|
| Person | 1 |
| helmet | 1 |
| vest | 1 |
| goggles | 1 |
| gloves | 2 |
| boots | 2 |

Genel YOLO26n sonucu:

| Tespit | Güven | Kutu `(x1, y1, x2, y2)` |
|---|---:|---|
| person | 0,907 | `(175,61; 57,43; 444,30; 631,70)` |

Tek çalıştırmanın Ultralytics süre kaydı: ön işleme 27,554 ms, model çıkarımı
46,520 ms ve son işleme 43,838 ms. Bu tek örnek bir performans kıyaslaması,
video FPS garantisi veya eşzamanlı kamera kapasitesi değildir.

## Sonucun anlamı

Genel model kişiyi doğru biçimde buldu. Ancak genel ağırlığın sınıf kataloğunda
`helmet`, `vest`, `goggles`, `gloves` ve `boots` sınıfları bulunmuyor. Bu nedenle
görüntüde açıkça görünen ekipmanlara ilişkin tespit üretmedi.

Buradaki kritik ayrım şudur: genel modelin “baret tespit etmemesi”, baretin eksik
olduğunu göstermez. Genel model bu soruyu cevaplayacak sınıflarla eğitilmemiştir.
PPE uygunluğu için Construction-PPE verisiyle özel ağırlık eğitilecek ve eksik
ekipman kararı tek karede “nesne bulunamadı” sonucuna indirgenmeyecektir.

## Üretilen yerel çıktılar

- `data/inference/b4/image999-source.jpg`
- `data/inference/b4/image999-general-yolo.jpg`
- `data/inference/b4/image999-report.json`

Bu dosyalar deneyi yeniden kontrol etmek içindir ve `.gitignore` kapsamındadır.
Git'te yalnız tekrar kullanılabilir betik ve bu ölçüm özeti bulunur.

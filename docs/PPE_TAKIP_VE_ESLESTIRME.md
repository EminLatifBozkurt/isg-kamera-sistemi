# PPE Takibi ve Ekipmanı Kişiye Eşleştirme — C3

## Neden takip gerekiyor?

Model her karede kişi ve ekipman kutuları bulur. Aynı insan sonraki karede yeni
bir olay gibi değerlendirilmemelidir. ByteTrack, yalnız aynı kamera oturumu
içinde kişiye geçici bir takip numarası verir. Bu numara çalışan kimliği veya
yüz tanıma sonucu değildir.

Yeni kamera/video oturumunda takip belleği sıfırlanır. Böylece örneğin önceki
oynatımdaki `track_id=2`, yeni oynatımda aynı çalışan kabul edilmez.

## Ekipman nasıl atanıyor?

Bir ekipman yalnız kişi kutusuna yakın diye doğrudan o kişiye yazılmaz:

- baret ve gözlük baş bölgesinde,
- yelek gövde bölgesinde,
- eldiven orta/yan bölgede,
- bot alt vücut bölgesinde aranır.

Ekipmanın kişi kutusu içinde kalan oranı, yatay merkez uzaklığı ve beklenen
dikey bölge birlikte puanlanır. İki kişi benzer puan alırsa durum `ambiguous`
olur; ekipman hiçbirine kesin verilmez. Uygun kişi yoksa `unassigned` kalır.

Bu üç sonuç önemlidir:

| Sonuç | Anlamı |
|---|---|
| `assigned` | Ekipman tek kişiye yeterince açık biçimde bağlandı. |
| `ambiguous` | Birden fazla kişi olası; eksik veya var kararı kesinleştirilmez. |
| `unassigned` | Ekipman hiçbir takipli kişinin beklenen bölgesinde değil. |

## Yerel deney

```powershell
.\.venv\Scripts\python.exe scripts\run_video_tracking.py `
  C:\video\ornek.mp4 `
  --model data\training\b6\b6-clean-positive-e20\weights\best.pt `
  --source-id demo-kamera --max-frames 120 --device 0
```

9 Kasım 2026 tarihindeki 15 karelik yerel deneyde bir kişi bütün karelerde aynı
takip numarasıyla izlendi. Model 15 insan, 15 baret, 15 yelek ve 32 bot tespiti
üretti; 62 ekipman tespiti bu kişiye atandı. Görüntü/video kaydedilmedi.

## İndirme koruması

Takip başlamadan yerel model ve `lap` bağımlılığı kontrol edilir.
`YOLO_AUTOINSTALL=False` ayarı Ultralytics'in eksik paketi kendiliğinden
kurmasını engeller. Eksik bileşende kullanıcı onayı olmadan internete çıkılmaz.

## Sınırlar

Deney yerel bir fotoğraftan oluşturulan kısa ve kontrollü videodur. Kalabalık,
örtülme, hızlı hareket, farklı kamera açısı ve gerçek iş yeri videosu ayrıca
ölçülmelidir. Tek karede ekipmanın kişiye atanması doğrudan ihlal olayı üretmez;
zamansal karar ve kamera/bölge kuralı E1 aşamasında eklenecektir.

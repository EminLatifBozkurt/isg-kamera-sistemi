# Temiz PPE Modeli ve Bağımsız Test — B6/B7

## Ne düzeltildi?

İlk veri setinde iş güvenliğiyle ilgisiz 300 görüntü bulunduğu için eski model
reddedildi. Toplam 1.416 görüntü görsel olarak denetlendi; 1.116 ilgili görüntü
korundu. Belirsiz `none` ve güvenilir olmayan dört `no_*` sınıfı çıkarıldı.

Yeni model yalnız görüntüde gerçekten görülebilen altı sınıfı algılar:

- baret (`helmet`)
- eldiven (`gloves`)
- yelek (`vest`)
- bot (`boots`)
- gözlük (`goggles`)
- insan (`Person`)

Bir ekipmanın eksik olduğu doğrudan ayrı bir sınıfla tahmin edilmez. Sonraki
aşamada kişi üzerinde gerekli ekipman bulunamazsa, kamera/bölge kuralı ve birden
fazla video karesi birlikte değerlendirilerek ihlal adayı oluşturulacaktır.

## Eğitim

| Ayar | Değer |
|---|---:|
| Başlangıç modeli | YOLO26n |
| Eğitim / doğrulama / test | 900 / 109 / 107 görüntü |
| Görüntü boyutu | 640 piksel |
| Grup büyüklüğü | 8 |
| Tur | 20 |
| Ekran kartı | NVIDIA GeForce RTX 3050 Ti Laptop GPU |

Doğrulama sonucu: precision 0,9002; recall 0,8103; mAP50 0,8868 ve mAP50-95
0,4930. En iyi ağırlığın SHA-256 özeti
`e76edec370c8b465529624b61f9e13d5afcdd29913912b82e69f6f8aa6344c38`.

## Eğitimde görülmeyen 107 görüntüde test

| Sınıf | Precision | Recall | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|
| baret | 0,9157 | 0,8977 | 0,9309 | 0,4848 |
| eldiven | 0,8639 | 0,6611 | 0,7767 | 0,3782 |
| yelek | 0,8667 | 0,8275 | 0,9107 | 0,5652 |
| bot | 0,9088 | 0,7230 | 0,8505 | 0,4884 |
| gözlük | 0,8377 | 0,6170 | 0,7408 | 0,3203 |
| insan | 0,8861 | 0,8722 | 0,9120 | 0,5501 |
| **Genel** | **0,8798** | **0,7664** | **0,8536** | **0,4645** |

Tek görüntülü değerlendirmede ön işleme, model ve son işleme toplamı görüntü
başına yaklaşık 38,4 ms; yaklaşık hız 26,0 FPS'tir. Tepe ayrılmış GPU belleği
67,1 MiB ölçüldü. Eğitim belleği ve gerçek video hattı tüketimi bundan farklıdır.

## Sonucun dürüst yorumu

Baret, insan ve yelek güçlü başlangıç sonuçları verdi. Gözlük ve eldiven daha
küçük/örtülebilen nesneler olduğu için diğer sınıflardan zayıf ve yeni veriyle
geliştirilmelidir. Test, veri içindeki temiz ve ayrılmış görüntülerde yapılmıştır;
farklı kamera yüksekliği, ışık, hareket bulanıklığı ve kalabalık saha henüz
ölçülmemiştir. Model tek başına güvenlik kararı vermez; İSG görevlisine inceleme
adayı üretmek için kullanılacaktır.

Büyük model ağırlıkları ve makineye özel sonuç JSON'u Git'e eklenmez. Yerel
çıktılar sırasıyla `data/training/b6/b6-clean-positive-e20/` ve
`data/evaluation/b7/b7-clean-positive-b1/` altında tutulur.

# Filtresiz İlk PPE Model Eğitimi — Kabul Edilmeyen Başlangıç Deneyi

> **Durum:** Bu model proje modeli olarak kullanılmayacaktır. Sonradan yapılan
> tam görsel denetimde veri setinin son 300 görüntüsünün iş güvenliğiyle ilgisiz
> spor, konser, toplantı, gündelik yaşam ve silahlı kişi sahneleri olduğu bulundu.
> Aşağıdaki sonuçlar yalnız sorunun nasıl fark edildiğini belgelemek içindir.

## Amaç

B5'te yapısal olarak temizlenen veriyi kullanarak küçük bir nesne algılama modelinin
PPE sınıflarını öğrenip öğrenemediğini görmek ve deneyin tekrar edilebilir bir
kaydını oluşturmaktır. Bu aşama nihai başarı ölçümü değildir; ayrılmış test
görüntüleri B7'ye kadar kullanılmamıştır.

## Kullanılan ayarlar

- Model: yerel YOLO26n başlangıç ağırlığı
- Veri: 1.138 eğitim, 140 doğrulama, 138 dokunulmamış test görüntüsü
- Sınıf sayısı: 11
- Görüntü boyutu: 640 piksel
- Eğitim turu: 20
- Grup boyutu: 8
- Rastgelelik tohumu: 20261109
- Donanım: NVIDIA GeForce RTX 3050 Ti Laptop GPU
- Ortam: Python 3.12.2, PyTorch 2.11.0+cu128, Ultralytics 8.4.194

Eğitim kesintiye uğradığı için `last.pt` kaydından devam ettirilerek tamamlandı.
Betik bu durumda önceki optimizer ve tur bilgisini korur. Girdi ve çıktıların
SHA-256 özetleri `experiment-record.json` içinde tutulur.

## Yeniden çalıştırma

```powershell
.\.venv\Scripts\python.exe scripts\train_ppe_model.py `
  --model data\models\yolo26n.pt `
  --data data\datasets\construction-ppe-b5\data.yaml `
  --name b6-baseline-e20 `
  --epochs 20 --image-size 640 --batch 8 `
  --device 0 --workers 2 --patience 8
```

Kesilen aynı deneye devam etmek için komuta şunlar eklenir:

```powershell
--resume-from data\training\b6\b6-baseline-e20\weights\last.pt
```

Betik eksik model veya veri dosyasını internetten indirmez. Var olan bir deney
klasörünün yanlışlıkla üzerine de yazmaz.

## Doğrulama sonucu

En iyi ağırlığın 140 doğrulama görüntüsündeki genel sonucu:

| Ölçüm | Sonuç |
|---|---:|
| Precision | 0,6254 |
| Recall | 0,5233 |
| mAP50 | 0,5423 |
| mAP50-95 | 0,2794 |

Baret için mAP50 0,917; yelek için 0,940 ölçüldü. Buna karşılık `no_helmet`
0,154, `no_goggle` 0,066, `no_gloves` 0,125 ve `no_boots` 0,006 mAP50 verdi.
Yani model ekipmanın varlığını bazı sınıflarda iyi bulurken ekipman eksikliğini
güvenilir biçimde ayırmayı henüz öğrenemedi.

## Sonucun anlamı ve sınırı

Bu değerler yalnız sorunlu doğrulama bölümüne aittir. Model seçilirken bu görüntülerden
yararlanıldığı için nihai başarı gibi sunulamaz. Reddedilen model 138 test
görüntüsünde ayrıca ölçülmedi. `no_helmet`, `no_goggle`, `no_gloves` ve `no_boots` örneklerinin
tamamının iş yeri dışı 300 görüntüden geldiği görülmüştür. Bu sınıflar ile anlamı
belirsiz `none` temiz eğitimden çıkarılmıştır. Yeni model yalnız helmet, gloves,
vest, boots, goggles ve Person sınıflarıyla ayrıca eğitilmiş ve bağımsız test
sonucu `TEMIZ_PPE_MODELI_VE_TESTI.md` içinde kaydedilmiştir.

Model ağırlıkları ve ayrıntılı deney çıktıları büyük/üretilmiş dosyalar olduğu
için `data/training/b6/b6-baseline-e20/` altında yerel tutulur ve Git'e eklenmez.

# PPE verisini temizleme ve güvenli ayırma

Deney tarihi: 9 Kasım 2026. Bu çalışma B5 görevinin çıktısıdır. Amaç, aynı
çekime ait çok benzer karelerin eğitim ve test bölümlerine dağılmasını önlemek ve
ham arşivi değiştirmeden tekrar üretilebilir bir çalışma veri seti hazırlamaktır.

## Neden yeniden ayırdık?

Construction-PPE arşivinde 1.416 görüntü hazır olarak `train`, `val` ve `test`
bölümlerine ayrılmıştır. Ancak arşiv, görüntülerin geldiği video veya çekim
oturumu kimliğini vermiyor. Hazır ayrımda aynı kişi ve aynı ortamın birbirine çok
benzeyen karelerinin farklı bölümlere düştüğü görüldü. Böyle bir durumda model,
test sırasında daha önce gördüğü sahnenin neredeyse aynısıyla karşılaşabilir ve
başarı olduğundan yüksek görünebilir.

## Hazırlama yöntemi

`scripts/prepare_yolo_dataset.py` aracı şu işlemleri yapar:

1. ZIP içindeki görüntü ve etiket eşleşmelerini okur.
2. Görüntüsü olmayan 10 artık etiketi çalışma kopyasına almaz.
3. `image187.txt` içindeki yinelenen etiket satırını bir kez yazar.
4. Her görüntü için 64 bit algısal özet (pHash) hesaplar.
5. Hamming uzaklığı en fazla 4 olan benzer görüntüleri tek grupta birleştirir.
6. Grupları parçalamadan, sınıf dağılımını da gözeterek yaklaşık %80 eğitim,
   %10 doğrulama ve %10 test biçiminde dağıtır.
7. Tohum değerini, kaynak arşiv özetini, her görüntünün grubunu ve yeni bölümünü
   `split-report.json` dosyasına kaydeder.

Ayırma tohumu `20261109` olarak sabittir. Aynı arşiv ve ayarlarla aynı sonuç
yeniden üretilir. Ham ZIP üzerinde hiçbir değişiklik yapılmaz.

## Gerçek sonuç

| Ölçüm | Hazır arşiv ayrımı | Hazırlanan ayrım |
|---|---:|---:|
| Eğitim görüntüsü | 1.132 | 1.138 |
| Doğrulama görüntüsü | 143 | 140 |
| Test görüntüsü | 141 | 138 |
| Bölümler arasındaki benzer görüntü çifti | 38 | 0 |
| Görüntü ve etiket çifti | 1.416 | 1.416 |

- Görsel benzerlik grubu sayısı: 1.299
- En büyük grup: 12 görüntü
- Temizlenen yinelenen etiket satırı: 1
- Hazırlanan yerel veri boyutu: yaklaşık 171,30 MiB
- Sınıf sayısı: 11

En büyük grubun örnekleri `image40`, `image1025` ve `image1038` görüntüleridir.
Bu kareler aynı kişi ve aynı merdiven ortamındaki yakın çekimlerdir. Hazır arşivde
bu grup eğitim, doğrulama ve test bölümlerine dağılmışken yeni ayrımda grubun 12
karesi de eğitim bölümünde tutuldu. Bu örnek görsel olarak da doğrulandı.

## Çalıştırma

```powershell
.\.venv\Scripts\python.exe scripts\prepare_yolo_dataset.py `
  data\datasets\construction-ppe.zip `
  data\datasets\construction-ppe-b5
```

Üretilen `data.yaml`, Ultralytics'in yerel veri denetimiyle açıldı. Eğitim,
doğrulama ve test yollarının tamamı bulundu; 11 sınıf doğru okundu. Çalışma
kopyası `data/` altında olduğu için GitHub'a gönderilmez.

## Gerçek video verileri için kaynak grubu

Gelecekte bir videodan kare çıkarıldığında yalnız görsel benzerliğe güvenmek
yerine kaynak kimliği verilmelidir. Araç, aşağıdaki sütunları içeren UTF-8 CSV
dosyasını `--source-groups` seçeneğiyle kabul eder:

```csv
image_member,source_group
images/train/frame001.jpg,kamera01-oturum01
images/train/frame002.jpg,kamera01-oturum01
```

Aynı `source_group` değerine sahip bütün kareler, görüntüleri farklı görünse bile
tek bölümde tutulur. Böylece bir videonun komşu kareleri eğitim ve teste bölünmez.

## Sınır ve doğru yorum

Construction-PPE arşivi gerçek kaynak/video kimliklerini yayımlamadığı için
algısal gruplar ortak kaynağı kesin olarak kanıtlamaz. Bu çalışma, ölçülebilen
yakın benzerlik sızıntısını kaldırır; bilinmeyen kaynak ilişkilerini varmış gibi
iddia etmez. Yeni çekilecek video verilerinde CSV kaynak kimliği zorunlu
tutulacaktır.

B5 çalışması sonrasında yapılan tam görsel denetim, 300 iş yeri dışı sahneyi
ortaya çıkardı. Bu nedenle burada anlatılan 11 sınıflı çalışma kopyası eğitimde
kullanılmadı; sahne filtreli altı sınıflı veri sürümü üretildi. Temiz modelin
eğitim ve test sonucu `TEMIZ_PPE_MODELI_VE_TESTI.md` içinde kaydedildi.

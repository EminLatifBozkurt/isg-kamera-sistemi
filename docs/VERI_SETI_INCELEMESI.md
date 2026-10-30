# PPE veri seti incelemesi

İnceleme tarihi: 30 Ekim 2026. Bu belge, ilk model deneyi için veri seçimini
gerekçelendirir. Sayısal bulgular resmî arşivin kendisi üzerinde
`scripts/audit_yolo_zip.py` ile ölçülmüştür.

## Karar

İlk teknik deneyde **Construction-PPE v1.0** kullanılacak. Bunun nedeni sınıf
listesinin projenin ilk adaylarıyla doğrudan örtüşmesi, YOLO biçiminde sunulması
ve AGPL-3.0 lisansının açık kaynak AGPL-3.0 proje düzenimizle uyumlu olmasıdır.

Bu veri seti, filtresiz hâliyle nihai ürün verisi olarak kabul edilmedi.
Etiket ve alan uyumu sorunları nedeniyle önce küçük bir temel model eğitilecek,
başarısız örnekler incelenecek ve gerekirse veri ayıklama/yeniden etiketleme
yapılacak. Model sonucu gerçek iş yeri güvenlik garantisi olarak sunulmayacak.

## İncelenen kaynaklar

| Veri seti | Kapsam | Lisans | Bu proje için karar |
|---|---|---|---|
| Construction-PPE v1.0 | 1.416 görüntü; baret, eldiven, yelek, bot, gözlük, kişi ve eksiklik bölgeleri | AGPL-3.0 | İlk temel deney |
| SH17 | 8.099 görüntü, 17 sınıf; vücut bölgeleri ve daha geniş PPE türleri | CC BY-NC-SA 4.0 | Ana eğitim verisi yapılmayacak |
| Pictor-PPE | İşçi, baret ve yelek ağırlıklı | Depo sayfasında açık lisans doğrulanamadı | Haklar netleşmeden kullanılmayacak |
| CPPE-5 | Tıbbi tulum, yüz siperi, eldiven, maske ve gözlük | Araştırma veri seti | İnşaat/üretim alanıyla uyuşmadığı için ilk deneyde yok |

SH17 daha büyük ve üretim ortamına yakın olsa da depo lisansı ticari kullanımı
sınırlıyor. Makalesindeki “ticari amaçla da kullanılabilir” ifadesiyle depo
lisansı arasında çelişki bulunduğundan daha kısıtlayıcı olan açık lisans metni
esas alındı. Gelecekte şirket içi kullanım hedefi korunacağı için SH17, açık bir
hak doğrulaması olmadan modele karıştırılmayacak.

## Construction-PPE resmî kaynak ve bütünlük kaydı

- Belge: https://docs.ultralytics.com/datasets/detect/construction-ppe/
- Arşiv: https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip
- Belgedeki sürüm: 1.0.0, Ocak 2025
- Arşiv boyutu: 178.415.813 bayt
- SHA-256: `bef8dcb599aa4e9d9f5e602cb6fa7143d3c84d7f6a0ff40463d7f2a4c2632ccc`
- Arşiv içindeki lisans: GNU AGPL-3.0
- Yerel konum: `data/datasets/construction-ppe.zip` (Git tarafından izlenmez)

SHA-256, ileride aynı arşivin kullanıldığını doğrulamak içindir; üreticinin
imzalı doğrulama değeri değildir.

## Gerçek arşiv denetimi

Resmî sayfadaki 1.132 eğitim, 143 doğrulama ve 141 test görüntüsü toplam 1.416
görüntü olarak arşivde doğrulandı. Buna karşılık 1.426 etiket dosyası var.
Eğitim bölümündeki 10 etiket dosyasının karşılık gelen görüntüsü yok:

`image95(1)`, `image940(1)`, `image941(1)`, `image944(1)`, `image945(1)`,
`image946(1)`, `image947(1)`, `image948(1)`, `image949(1)`, `image950(1)`.

Ek olarak `labels/train/image187.txt` içinde aynı kişi kutusu iki kez bulunuyor.
Geçersiz koordinat veya etiketsiz görüntü bulunmadı. Eğitimden önce 10 artık
etiket dışarıda bırakılacak ve yinelenen satır temizlenecek. Temizleme işlemi
ham ZIP'i değiştirmeyecek; türetilmiş veri ve yapılan değişiklikler kaydedilecek.

## Sınıf dağılımı ve kutu büyüklükleri

“%1’den küçük”, etiket kutusunun tüm görüntü alanının yüzde 1’inden azını
kapladığı anlamına gelir. Bu değer doğrudan başarısızlık demek değildir fakat
uzak CCTV görüntülerinde küçük nesne tespitinin zor olacağını gösterir.

| Sınıf | Örnek sayısı | Bulunduğu görüntü | Kutuların %1’den küçüğü |
|---|---:|---:|---:|
| helmet | 1.750 | 1.057 | %43,8 |
| gloves | 1.461 | 714 | %72,6 |
| vest | 1.632 | 1.057 | %9,5 |
| boots | 1.613 | 677 | %40,1 |
| goggles | 526 | 488 | %75,9 |
| none | 800 | 427 | %19,0 |
| Person | 2.265 | 1.349 | %1,4 |
| no_helmet | 485 | 283 | %28,7 |
| no_goggle | 411 | 265 | %76,9 |
| no_gloves | 556 | 236 | %50,4 |
| no_boots | 115 | 36 | %78,3 |

`no_boots`, yalnız 36 görüntüde 115 örnekle en zayıf eksiklik sınıfıdır.
Gözlük ve eldiven kutularının çoğu da çok küçüktür. Bu nedenle geniş katalog
arayüzde hemen “güvenilir” olarak işaretlenmeyecek.

## Etiket anlamı ve alan uyumu

Örnekler görsel olarak incelendi. `no_helmet`, `no_goggle`, `no_gloves` ve
`no_boots` kutuları eksik nesnenin kendisini değil, çoğunlukla baretsiz baş,
gözlüksüz yüz/göz, eldivensiz el ve iş botsuz ayak bölgesini işaretliyor. Bu,
eksikliği doğrudan sınıflandırmaya yarayabilir; ancak normal ayakkabının her iş
alanında ihlal sayılması gibi alan kuralını model sınıfından ayırmayı gerektirir.

`none` sınıfının resmî belgede kesin açıklaması yok. Görsel örneklerde yeleksiz
gövdeyi işaretlediği gözlendi; bu bir **çıkarımdır** ve eğitimden önce daha geniş
örnekleme ile doğrulanacaktır. Resmî sayfada ayrıca ayrı bir `no_vest` sınıfı
olmadığı belirtiliyor. Kod içinde `none = no_vest` dönüşümü henüz yapılmayacak.

Veri setinde inşaat çalışanlarının yanında ofis, spor, gündelik yaşam, ünlü ve
tıbbi görüntüler de bulunuyor. Bu çeşitlilik vücut bölgesi öğrenmeye katkı
sağlayabilir fakat hedef CCTV alanından farklıdır. Rastgele görüntü ayırmak aynı
kaynaktan benzer görüntülerin eğitim ve teste sızması riskini de taşıyabilir.

## İlk ekipman adayları

| Ekipman | İlk deney durumu | Gerekçe |
|---|---|---|
| Baret | Ana aday | Görece fazla örnek; eksiklik sınıfı var |
| Yelek | Ana aday | Büyük kutular ve çok örnek; `none` anlamı doğrulanmalı |
| Eldiven | Deneysel | Çok sayıda örnek, fakat kutular küçük ve el görünürlüğü kritik |
| Gözlük | Deneysel | Az ve çok küçük örnek; yakın kamera gerektirebilir |
| Bot | Deneysel | Kullanım sınıfı var; `no_boots` çok az ve iş botu standardı görüntüden kesinleşmez |

İlk eğitim tüm resmî sınıflarla temel karşılaştırma sağlayabilir; kullanıcıya
sunulan “desteklenen ekipman” listesi ise sınıf başına test sonuçları görülmeden
kesinleştirilmeyecek. İlk işlevsel sistem hedefi baret ve yelektir; diğer üç
ekipman katalogdan silinmez, “deneysel/değerlendirilemiyor” durumunu korur.

## Sonraki veri adımı

1. Demo için kullanabileceğimiz fotoğraf ve videoların izinlerini kaydet.
2. Arşivden temizlenmiş, sürümlü bir çalışma kopyası üreten hazırlama aracını yaz.
3. Kaynak benzerliği ve olası kopyaları denetleyerek eğitim/doğrulama/test ayrımını gözden geçir.
4. GPU kurulumu sonrası küçük modelle temel deney yap; sınıf başına sonuçları ölç.

## Kaynaklar

- Construction-PPE resmî belgesi: https://docs.ultralytics.com/datasets/detect/construction-ppe/
- SH17 resmî deposu: https://github.com/ahmadmughees/SH17dataset
- SH17 makalesi: https://arxiv.org/abs/2407.04590
- Pictor-PPE resmî deposu: https://github.com/ciber-lab/pictor-ppe
- CPPE-5 makalesi ve veri açıklaması: https://pmc.ncbi.nlm.nih.gov/articles/PMC10018606/

# Uygulama ilerlemesi

## 30 Ekim 2026 — İlk küçük uygulama adımı tamamlandı

### Yapılanlar

- Doğru yerel depo ve uzak GitHub adresi doğrulandı; mevcut AGPL lisansı korundu.
- Gereksinim, teknoloji ve tasarım belgeleri depoya alındı.
- Bağımlılık sırası, çıktı ve tamamlanma ölçütleriyle görev listesi yazıldı.
- Ayrı Python 3.12 sanal ortamı ve sunucu/test paketleri kuruldu.
- Kurulu paket sürümleri requirements-dev.lock.txt içinde kaydedildi.
- FastAPI sunucusu ve çalışma durumu adresi eklendi.
- Kamera temel kuralları ile aktif bölgelerin ek şartlarını birleştiren kod yazıldı.
- Ekipman gözlemi uygun / ihlal adayı / değerlendirilemiyor olarak ayrıldı.
- Önemli kod bölümlerine Türkçe açıklamalar ve README'ye çalıştırma adımları eklendi.
- Gizli ayar, model, video ve veri dosyaları için Git dışlama kuralları eklendi.

### Gerçekleştirilen kontroller

| Kontrol | Sonuç |
|---|---|
| pytest | 5 test geçti |
| Ruff kod kontrolü | Geçti |
| Ruff biçim kontrolü | 7 Python dosyası uygun |
| pip check | Bozuk bağımlılık yok |
| Gerçek HTTP çalışma durumu isteği | 200; analiz/veritabanı not_configured |
| Gerçek HTTP OpenAPI isteği | 200; health adresi belgede var |
| Git dışlama kontrolü | .env, video, model ve .venv dışarıda; .env.example paylaşılabilir |
| Yerel ortam aracı | Python 3.12.2; RTX 3050 Ti Laptop GPU, 4096 MiB VRAM |

HTTP kontrolü için geçici sunucu başlatıldı ve kontrolden sonra durduruldu.
Bu aşamada testler elle hazırlanmış gözlemlerle iş kuralını doğrular; kamera
veya yapay zekâ doğruluğuna ilişkin bir başarı sonucu değildir.

### Sıradaki küçük adım

Veri/lisans incelemesi ve ilk ekipman kapsamını doğrulama. Ardından uygun
PyTorch/CUDA kurulumu ve küçük bir model deneyi. Görüntü analizi, veri tabanı,
web paneli, kullanıcı oturumu ve bildirimler henüz uygulanmadı.

Bu adım, aşağıdaki veri seti incelemesiyle birlikte `b02bbce` numaralı Git
kaydına alındı ve GitHub `main` dalına gönderildi.

## 30 Ekim 2026 — PPE veri seti seçimi ve denetimi

- Construction-PPE ve SH17 başta olmak üzere resmî veri kaynakları karşılaştırıldı.
- AGPL-3.0 lisanslı Construction-PPE, ilk temel deney için seçildi.
- 178.415.813 baytlık resmî arşiv indirildi ve SHA-256 değeri kaydedildi.
- 1.416 görüntü, 1.426 etiket dosyası ve 11 sınıf doğrudan arşivden denetlendi.
- Görüntüsü olmayan 10 etiket dosyası ve bir yinelenen etiket satırı bulundu.
- Küçük nesne oranları ölçüldü; gözlük, eldiven ve `no_boots` sınıflarındaki
  riskler belgelendi.
- Etiket örnekleri görsel incelendi; eksiklik sınıflarının vücut bölgesi
  kutuları olduğu ve verinin hedef alan dışı görüntüler içerdiği kaydedildi.
- Tekrar kullanılabilir `scripts/audit_yolo_zip.py` denetim aracı eklendi.

Veri seti ve üretilen görsel/JSON denetim çıktıları `data/` altında tutuluyor ve
Git'e eklenmiyor. Model kurulumu veya eğitimi henüz yapılmadı. Sıradaki görev,
izinli demo fotoğraf/video kaynaklarını belirlemek (B2).

## 30 Ekim 2026 — Demo görüntü kaynakları belirlendi

- Construction-PPE test görüntüleri ilk sabit model testi için seçildi.
- Pexels lisansı ve kullanım sınırlamaları resmî sayfadan incelendi.
- Baret ve yelek bulunan iki pozitif Pexels video adayı kaydedildi.
- Stok görüntülerdeki kişiler ihlal yapmış gibi gösterilmeyecek.
- Eksik ekipman senaryosu için güvenli ve onaylı kendi canlandırma yöntemi seçildi.
- İzinsiz güvenlik kamerası, kaynağı belirsiz video ve yüz tanıma verisi kapsam dışı bırakıldı.
- Görüntülerin Git'e eklenmemesi ve yerel kaynak kaydı kuralları belgelendi.
- Kullanıcının ilerlemeyi görebilmesi için B4 sonrasına ilk gerçek web arayüzü
  teslimi eklendi.

B2 tamamlandı. Henüz Pexels videosu indirilmedi; model kurulumu ve ilk sabit
görüntü çıkarımı için gerekli değil. Sıradaki görev GPU destekli PyTorch/model
kurulumu ve küçük tensör doğrulaması (B3).

## 30 Ekim 2026 — CUDA ve model çalışma ortamı doğrulandı

- Python 3.12 sanal ortamına PyTorch 2.11.0+cu128 ve torchvision
  0.26.0+cu128 kuruldu.
- Ultralytics 8.4.194 ve OpenCV 5.0.0 içe aktarılarak doğrulandı.
- PyTorch CUDA 12.8 çalışma zamanını ve NVIDIA GeForce RTX 3050 Ti Laptop
  GPU'yu gördü; kullanılabilir VRAM 4,0 GiB olarak raporlandı.
- 2048x2048 matris çarpımı `cuda:0` üzerinde tamamlandı. İlk doğrulama ölçümü
  56,8 ms sürdü; bu değer model FPS veya gerçek zamanlı performans iddiası değildir.
- Kurulumu tekrarlanabilir tutmak için CUDA PyTorch ve görüntü paketleri ayrı
  sabit sürüm dosyalarına kaydedildi.
- `scripts/check_cuda.py`, model ağırlığı indirmeden aynı kontrolü tekrar
  çalıştırmak için eklendi.
- Büyük internet indirmeleri için boyutun önceden bildirilmesi ve kullanıcıdan
  açık onay alınması proje çalışma kuralına eklendi.

B3 tamamlandı. Henüz herhangi bir YOLO model ağırlığı indirilmedi ve görüntü
çıkarımı yapılmadı. Sıradaki görev, boyutu önceden bildirilecek hazır nano model
ağırlığıyla Construction-PPE görüntüsünde ilk kontrollü çıkarım (B4).

## 30 Ekim 2026 — İlk tek-görüntü model çıkarımı tamamlandı

- Kullanıcıya 5.544.453 baytlık dosya boyutu bildirildi ve açık onay alındı.
- Resmî `yolo26n.pt` genel nesne ağırlığı indirildi; SHA-256 değeri kaydedildi.
- Construction-PPE test bölümündeki `image999.jpg` örneği seçildi.
- Veri etiketi 1 kişi, 1 baret, 1 yelek, 1 gözlük, 2 eldiven ve 2 bot içeriyor.
- Genel model kişiyi 0,907 güvenle buldu; baret, yelek, gözlük, eldiven ve bot
  genel modelin sınıf kataloğunda bulunmadığı için bu ekipmanları tespit etmedi.
- İlk çalıştırmada model çıkarım aşaması 46,520 ms sürdü. Bu tek örnekten video
  FPS'si veya kamera kapasitesi sonucu çıkarılmadı.
- Yerel ağırlık yoksa otomatik indirme yapmayan, açıklamalı
  `scripts/run_single_image_inference.py` betiği eklendi.
- Kaynak, işaretlenmiş görüntü ve JSON raporu Git dışındaki `data/inference/b4/`
  klasöründe üretildi.
- Deney komutu, gerçek sonuç ve doğru yorum `ILK_MODEL_DENEYI.md` içinde
  belgelendi.

B4 tamamlandı. Genel modelin çalışması PPE modelinin hazır olduğu anlamına
gelmiyor. Kullanıcının kod değişikliklerini tarayıcıda görebilmesi için sıradaki
teslim V1: React/TypeScript arayüz temeli ve ana panel iskeleti.

## 31 Ekim 2026 — İlk görünür web paneli hazır

- `frontend/` altında React 19.3.1, TypeScript 6.0.3 ve Vite 8.3.5 uygulaması kuruldu.
- Material UI 9.5.0 ile İSG kontrol merkezine uygun responsive tasarım hazırlandı.
- Genel Bakış, Kameralar, Olaylar ve Çalışanlar sayfaları React Router ile bağlandı.
- Ana panel gerçek `/api/v1/health` adresini Vite proxy üzerinden çağırıyor.
- API çalışıyorsa hizmet adı ve sürümü gösteriliyor; analiz ile veritabanı hazır
  değilse `Bağlı değil` olarak görünüyor.
- Kamera, olay ve çalışan kayıtları henüz olmadığı için sahte liste/sayı üretilmedi.
- Hazır olmayan ekleme ve filtre düğmeleri devre dışı bırakıldı.
- Masaüstü 1440x900 ve mobil 390x844 görünümünde yatay taşma olmadığı doğrulandı.
- Mobil çekmece menüsü ve tüm sayfa yönlendirmeleri tarayıcıda denendi.
- ESLint, TypeScript kontrolü ve Vite üretim derlemesi geçti; npm denetiminde
  bilinen güvenlik açığı bulunmadı.
- Yerel sayfa `200`, Vite üzerinden FastAPI health yanıtı `status=ok` döndürdü.
- Panel yalnız yerel adreste açıldı; harici Sites yayını veya bulut kurulumu yapılmadı.

V1 ve V2 tamamlandı. V3'ün çalıştırma komutları README'ye eklendi; kalıcı ekran
görüntüsü henüz eklenmediği için V3 tamamlandı olarak işaretlenmedi.

## 31 Ekim 2026 — Tek tıkla proje başlatıcı eklendi

- Depo köküne çift tıklanabilen `PROJEYI_BASLAT.cmd` eklendi.
- Başlatıcı FastAPI ve Vite süreçlerini gizli arka plan süreçleri olarak açıyor,
  iki HTTP adresinin hazır olmasını bekliyor ve paneli tarayıcıda açıyor.
- Eksik `.venv` veya arayüz paketlerinde otomatik indirme yapmak yerine Türkçe
  hata mesajı gösteriyor.
- Portlar başka uygulama tarafından kullanılıyorsa ilgili süreci kapatmadan
  güvenli biçimde duruyor.
- Başlatıcının açtığı süreçleri kapatmak için `PROJEYI_DURDUR.cmd` eklendi.
- Süreç kimlikleri ve loglar Git dışındaki `data/runtime/` klasöründe tutuluyor.

## 9 Kasım 2026 — Eğitim verisi temizlendi ve yeniden ayrıldı

- Ham Construction-PPE ZIP dosyasını değiştirmeyen
  `scripts/prepare_yolo_dataset.py` aracı eklendi.
- 1.416 görüntünün tamamı algısal benzerlik açısından karşılaştırıldı.
- Hazır eğitim/doğrulama/test ayrımında bölümler arasına dağılmış 38 benzer
  görüntü çifti bulundu.
- Benzer kareler 1.299 grup altında toplandı; en büyük grup 12 görüntü içeriyor.
- Gruplar parçalanmadan yaklaşık %80/%10/%10 oranında yeniden dağıtıldı.
- Yeni ayrım 1.138 eğitim, 140 doğrulama ve 138 test görüntüsü içeriyor.
- Yeni ayrımda bölümler arasındaki benzer görüntü çifti sayısı sıfırlandı.
- Görüntüsü olmayan 10 artık etiket dışarıda bırakıldı ve bir yinelenen etiket
  satırı temizlendi.
- Gelecekteki videolarda bütün kareleri kaynak/oturum kimliğiyle aynı bölümde
  tutmak için isteğe bağlı CSV grup desteği eklendi.
- Üretilen 171,30 MiB çalışma verisi `data/` altında tutuluyor ve Git'e girmiyor.
- Üretilen `data.yaml`, Ultralytics ile kontrol edildi; üç bölüm yolu ve 11 sınıf
  doğru bulundu.
- Veri hazırlama mantığı için beş yeni test eklendi; toplam on test geçti.

Construction-PPE gerçek çekim/video kimliği sağlamadığı için görsel benzerlik
gruplarının ortak kaynağı kesin kanıtlamadığı açıkça belgelendi. B5 tamamlandı;
sıradaki ana görev, hazırlanmış veriyle küçük PPE modelini eğitmek (B6).

## 9 Kasım 2026 — Filtresiz başlangıç modeli eğitildi

- `scripts/train_ppe_model.py` ile yalnız yerel veri ve yerel YOLO26n başlangıç
  ağırlığı kullanan, otomatik indirme yapmayan eğitim akışı eklendi.
- Eğitim kesilirse aynı deneyin `last.pt` kaydından devam etme desteği eklendi ve
  yarıda kalan ana deney bu yolla tamamlandı.
- Model 1.138 eğitim görüntüsüyle, 640 piksel görüntü boyutu, 8'li grup ve 20 tur
  ayarlarıyla RTX 3050 Ti üzerinde eğitildi.
- En iyi ağırlık 140 doğrulama görüntüsünde precision 0,6254, recall 0,5233,
  mAP50 0,5423 ve mAP50-95 0,2794 verdi.
- Baret ve yelek sınıfları güçlü görünürken `no_helmet`, `no_goggle`,
  `no_gloves` ve `no_boots` sınıfları zayıf kaldı. Bu sonuç gizlenmeden sonraki
  ölçümün önceliği olarak kaydedildi.
- Deney girdileri, sürümler, dosya özetleri ve çıktı ağırlıkları
  `experiment-record.json` dosyasına yazıldı; büyük çıktılar Git dışında tutuldu.
- Eğitim yardımcılarının dosya özeti, güvenli deney adı, devam kaydı ve veri kaydı
  davranışı için on test eklendi; veri hazırlama testleriyle birlikte 15 test geçti.

Bu çalışma daha sonra yapılan tam sahne denetimi nedeniyle B6'nın tamamlanması
olarak kabul edilmedi. Sonuçlar proje başarısı değildir.

## 9 Kasım 2026 — Veri setinin sahne kapsamı düzeltildi

- 1.416 görüntünün tamamı, dosya adı ve benzerlik grubu görünen 23 temas
  sayfasında görsel olarak incelendi.
- `image1117` ile `image1416` arasındaki 300 görüntünün spor, konser, toplantı,
  gündelik yaşam, silahlı kişiler ve benzeri iş güvenliği dışı sahneler olduğu
  doğrulandı.
- Bu 300 görüntünün `no_helmet`, `no_goggle`, `no_gloves` ve `no_boots`
  örneklerinin tamamını içerdiği ölçüldü. Bu nedenle filtresiz modelin eksik
  ekipman başarısı geçersiz kabul edildi.
- Belirsiz `none` sınıfı ve dört uygunsuz `no_*` sınıfı temiz eğitimden çıkarıldı.
- Yeni veri sürümü helmet, gloves, vest, boots, goggles ve Person olmak üzere
  altı sınıf içeriyor: 900 eğitim, 109 doğrulama ve 107 test görüntüsü.
- Sahne kararları kaynak arşiv özetiyle kaydedildi; hiçbir benzerlik grubunun
  kısmen tutulup kısmen çıkarılmadığı doğrulandı.
- Ham arşiv, B5 verisi ve filtresiz ilk model silinmedi; karşılaştırma ve denetim
  kanıtı olarak Git dışındaki `data/` klasöründe kaldı.

## 9 Kasım 2026 — Temiz PPE modeli eğitildi ve bağımsız test edildi

- YOLO26n, yalnız altı görünür sınıfı içeren 900 temiz eğitim görüntüsüyle,
  640 piksel, 8'li grup ve 20 tur ayarlarında sıfırdan yeniden eğitildi.
- 109 doğrulama görüntüsünde precision 0,9002, recall 0,8103, mAP50 0,8868 ve
  mAP50-95 0,4930 ölçüldü.
- Model seçimi bittikten sonra, eğitim ve doğrulamada hiç kullanılmayan 107 test
  görüntüsü `scripts/evaluate_ppe_model.py` ile yalnız bir kez ölçüldü.
- Bağımsız testte precision 0,8798, recall 0,7664, mAP50 0,8536 ve mAP50-95
  0,4645 elde edildi.
- Sınıf mAP50 sonuçları: baret 0,9309; insan 0,9120; yelek 0,9107; bot 0,8505;
  eldiven 0,7767; gözlük 0,7408. Eldiven ve gözlük sonraki veri geliştirmesinde
  önceliklidir.
- RTX 3050 Ti üzerinde tek görüntülü testte işleme hattı görüntü başına yaklaşık
  38,4 ms, yani yaklaşık 26,0 FPS verdi. Bu ölçüm kamera okuma ve olay kaydını
  içermez.
- Ultralytics'in değerlendirme başında 755 KB yazı tipini otomatik indirdiği
  fark edildi. Betikler, bundan sonra sistemdeki yerel fontu hazırlayacak ve
  bulunamazsa internete çıkmak yerine duracak şekilde düzeltildi.
- Veri denetimi, filtreleme, eğitim kaydı, değerlendirme ve mevcut API/kurallar
  dahil toplam 37 Python testi geçti; Ruff kod ve biçim kontrolleri temiz.

B6 ve B7 tamamlandı. Model görünür ekipmanı algılar; “eksik ekipman” kararı,
sonraki aşamada kişi–ekipman eşleştirmesi ve kamera/bölge kurallarıyla üretilecektir.
Bu sonuç saha güvenliği için üretim onayı değildir; sıradaki model görevi kayıtlı
videoda zamansal kararlılık ve kişi–ekipman ilişkilendirmesidir.

## 9 Kasım 2026 — Kayıtlı video oturumu eklendi

- `isg_api.video_source` modülü kayıtlı videoyu OpenCV ile açacak şekilde eklendi.
  OpenCV yalnız video özelliği kullanıldığında yükleniyor; temel API başlangıcı
  gereksiz yere görüntü paketine bağlanmıyor.
- Her video açılışı benzersiz oturum kimliği, kaynak kimliği, başlangıç zamanı,
  FPS, kare sayısı ve çözünürlük bilgisi taşıyor.
- Her karede oturum kimliği, sıfırdan başlayan kare numarası, videonun kendi
  saniyesi ve bilgisayarda gözlemlendiği UTC zamanı birlikte tutuluyor.
- Normal mod videonun kaynak zamanına göre bekliyor; analiz deneyi için hızlı mod
  kaynak hızını beklemeden okuyabiliyor.
- Video yeniden açıldığında yeni `tracking_scope` üretiliyor. Böylece C3'te
  eklenecek takip numaraları eski oynatım veya başka oturumla birleşmeyecek.
- Bozuk/tekrarlanan kapsayıcı zamanında FPS tabanlı güvenli zaman kullanılıyor;
  geçersiz FPS, açılamayan dosya ve ikinci kez kullanılan oturum reddediliyor.
- Yerel PPE test görüntüsünden Git dışındaki `data/runtime` alanında 640×360,
  10 FPS ve 30 karelik geçici video üretildi. Normal hızlı okumada 30 kare ve
  0,0–2,9 saniye kaynak zamanı doğrulandı; ikinci açılış yeni oturum kimliği verdi.
- Video oturumu için 10 yeni test eklendi; projenin toplam 47 Python testi geçti.
  Ruff kod ve biçim denetimleri de temiz sonuç verdi.

C1 tamamlandı. Sıradaki görev C2: webcam kaynağını aynı oturum modeline eklemek
ve açılma, kapanma, bağlantı hatası durumlarını açık biçimde raporlamak.

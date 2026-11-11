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

## 9 Kasım 2026 — Webcam kaynağı ve bağlantı durumları eklendi

- `isg_api.webcam_source` modülü webcam'i yalnız gerektiğinde OpenCV ile açacak
  ve her bağlantıya benzersiz oturum kimliği verecek şekilde eklendi.
- Kaynak durumu `idle`, `opening`, `streaming`, `stopped`, `unavailable` ve
  `read_error` değerleriyle açıkça ayrıldı. Kamera kesintisi normal kapanış gibi
  gösterilmiyor.
- Son alınan karenin UTC zamanı ve oturumdaki kare sayısı değişmez durum kopyası
  üzerinden API/arayüz tarafından okunabilecek biçimde tutuluyor.
- Aynı webcam için eşzamanlı ikinci oturum reddediliyor. Kamera kapatılıp yeniden
  açıldığında yeni oturum ve takip kapsamı oluşuyor.
- FPS bilgisini vermeyen webcam'ler tamamen reddedilmiyor; bildirilen FPS boş
  bırakılıyor. Negatif aygıt numarası ve boş kaynak kimliği baştan engelleniyor.
- `scripts/inspect_webcam.py` görüntüleri göstermeden, diske yazmadan ve modele
  göndermeden sınırlı donanım denemesi yapacak şekilde eklendi.
- Acer Nitro 5'in 0 numaralı dahili kamerası gerçek OpenCV ile açıldı. Kamera
  640×480 ve 30 FPS bildirdi; beş kare başarıyla okundu ve bağlantı `stopped`
  durumuyla kapatıldı. Hiçbir görüntü saklanmadı.
- Webcam yaşam döngüsü için 12 yeni test eklendi; projenin toplam 59 Python
  testi geçti. Ruff kod ve biçim kontrolleri temiz sonuç verdi.

C2 tamamlandı. Sıradaki görev C3: PPE modelini video karelerine bağlamak,
ByteTrack ile kişileri oturum içinde takip etmek ve ekipmanı doğru kişiye
atarken belirsizliği korumak.

## 9 Kasım 2026 — ByteTrack ve ekipman–kişi eşleştirmesi eklendi

- Temiz PPE modeli kayıtlı video karelerine bağlandı. Ultralytics'in paketle
  gelen `bytetrack.yaml` yapılandırması aynı oturumdaki tespit numaralarını
  kareler arasında sürdürüyor.
- Yeni kamera/video oturumu başladığında mevcut ByteTrack belleği ve numara
  sayacı sıfırlanıyor. Başka oturuma ait kare etkin takipçiye verilemiyor.
- Baret/gözlük baş, yelek gövde, eldiven orta/yan ve bot alt vücut bölgesinde
  aranıyor. Ekipman kutusunun kişi kutusu içindeki oranı ve yatay yakınlığı
  birlikte değerlendiriliyor.
- İki kişinin aday puanı birbirine yakınsa ekipman hiçbirine kesin olarak
  yazılmıyor; iki kişi için de belirsiz gözlem olarak korunuyor. Takip kimliği
  henüz doğrulanmamış kişi de kesin eşleştirmede kullanılmıyor.
- Kontrollü testlerde yan yana iki kişiden birinin bareti diğerine yazılmadı;
  üst üste binen iki kişide ortadaki baret belirsiz kaldı; ayak hizasındaki nesne
  baret sayılmadı.
- İlk gerçek denemede gövdesi kadraj dışında kalan kişi algılanmadı ve yalnız
  görünen baret sahipsiz kaldı. Bu davranış doğru kabul edildi; sistem görünmeyen
  kişiye ekipman uydurmadı.
- Tam vücudu görünen yerel PPE fotoğrafından oluşturulan 15 karelik hafif
  hareketli videoda kişi bütün karelerde tek `track_id=2` ile izlendi. 15 insan,
  15 baret, 15 yelek ve 32 bot tespiti oluştu; 62 ekipman tespiti kişiye bağlandı.
- ByteTrack ilk çalıştırmada eksik `lap` paketini beklenmedik biçimde otomatik
  indirip kurdu (1,5 MB). Bu hata kaydedildi; `YOLO_AUTOINSTALL=False` koruması
  ve başlamadan bağımlılık denetimi eklendi. Bundan sonra eksik paket, kullanıcı
  onayı olmadan kurulmayacak.
- Takip ve eşleştirme için dokuz yeni test eklendi; projenin toplam 68 Python
  testi geçti. Ruff kod ve biçim kontrolleri temiz sonuç verdi.

C3 tamamlandı. Bu kontrollü sonuç gerçek kalabalık saha başarısı değildir.
Sıradaki C4 görevi, analiz yavaşladığında eski karelerin sınırsız birikmesini
engelleyen sınırlı kuyruk ile güncellik/donma durumlarını eklemektir.

## 9 Kasım 2026 — Sınırlı kare kuyruğu ve güncellik durumu eklendi

- `LatestFrameQueue`, canlı görüntü analizinde RAM'in sınırsız büyümemesi için
  varsayılan iki kare kapasiteli olarak eklendi.
- Kuyruk doluyken yeni kare geldiğinde üretici bekletilmiyor; en eski kare
  düşürülüp en güncel görüntü korunuyor. Alınan, işlenen ve düşen kare sayıları
  ayrı tutuluyor.
- Yeni kamera oturumu başladığında kuyruktaki eski kareler ve sayaçlar temizleniyor.
  Başka oturuma ait karenin yanlışlıkla eklenmesi veya işlenmesi reddediliyor.
- Son görüntü yaşı, son işleme zamanı ve görüntünün alınmasından analizin bitişine
  kadar geçen süre ölçülüyor.
- Durumlar `idle` (henüz kare yok), `healthy`, `backlog` (kuyruk dolu), `stale`
  (görüntü donmuş/eski) ve `stopped` olarak açıkça ayrıldı.
- Kapasite, en eski kareyi düşürme, oturum sıfırlama, donma eşiği, işleme
  gecikmesi, kapanış ve zaman aşımı için altı yeni test eklendi.
- Projenin toplam 74 Python testi geçti; Ruff kod ve biçim kontrolleri temiz.

C4 tamamlandı. Sıradaki C5 görevi, RTX 3050 Ti üzerindeki gerçek sonuçlara göre
ikinci eşzamanlı kaynak/ağ akışı sınırını değerlendirmektir. Mevcut tek-kare
ölçümleri yaklaşık 26 FPS gösterse de kamera okuma, takip ve kuyruk birlikte
ölçülmeden iki kaynak desteği vaat edilmeyecektir.

## 9 Kasım 2026 — Bir ve iki kaynak kapasitesi ölçüldü

- `scripts/benchmark_multi_source.py`, aynı yerel model/video/çözünürlükte bir
  ve iki bağımsız ByteTrack kaynağını karşılaştıracak şekilde eklendi.
- Her senaryoda kaynak başına üç ısınma karesi modelin ilk yükleme etkisini
  ölçüm dışında bıraktı; ardından kaynak başına 12 kare ölçüldü.
- Tek kaynakta 73,612 FPS, ortalama takip çağrısı 11,390 ms, tepe ayrılmış GPU
  belleği 65,197 MiB ölçüldü.
- İki kaynakta toplam 69,969 FPS, kaynak başına 34,985 FPS, ortalama takip
  çağrısı 12,055 ms ve tepe ayrılmış GPU belleği 83,062 MiB ölçüldü.
- Her kaynak ayrı model/takip durumu kullandı; takip kimlikleri kaynaklar arasında
  karışmadı. Ölçüm 640 piksel ve kısa/hafif hareketli yerel videoya aittir.
- Proje için başlangıç hedefi kaynak başına 5 FPS olarak açıkça kaydedildi.
  Ölçülen en büyük sayı iki olduğu için bu sürümün yapılandırma sınırı en fazla
  iki eşzamanlı kaynak oldu; üç veya daha fazla kaynak destekleniyor denmeyecek.
- Kullanılabilir gerçek RTSP kamera olmadığı için ağ gecikmesi, kopma ve yeniden
  bağlanma ölçülmedi. Ağ akışı kodda etkinleştirilmeyecek; webcam ve kayıtlı
  video desteklenen kaynaklar olarak kalacak.
- Ölçüm raporu Git dışındaki
  `data/evaluation/c5/c5-local-1v2-final/c5-capacity-report.json` dosyasına yazıldı.
- Kapasite karar mantığı için dört yeni test eklendi; projenin toplam 78 Python
  testi geçti. Ruff kod ve biçim kontrolleri temiz sonuç verdi.

C5 tamamlandı ve C bölümü bitti. Sıradaki ana görev D1: PostgreSQL geliştirme
kurulumunu ve gizli bilgileri depoya koymayan bağlantı ayarlarını hazırlamaktır.

## 9 Kasım 2026 — PostgreSQL bağlantı hazırlığı yapıldı (D1 devam ediyor)

- Bilgisayarda `psql`, PostgreSQL Windows servisi, Docker ve Podman bulunmadığı
  doğrulandı; var olmayan veritabanı kurulmuş gibi gösterilmedi.
- `Settings` içine 127.0.0.1/5432 varsayımları, veritabanı/kullanıcı adı, 1–20
  arası havuz boyutu ve `SecretStr` parola alanı eklendi.
- Parola yoksa `database_configured` false kalıyor. Parola ayar nesnesinin veya
  güvenle gösterilebilen bağlantı hedefinin metninde açığa çıkmıyor.
- `create_database_engine`, paketler ve parola hazır olmadan otomatik kurulum
  yapmıyor; açık hata veriyor. Hazır olduğunda `postgresql+psycopg` ve
  `pool_pre_ping` ile sınırlı bağlantı havuzu oluşturacak.
- `check_database_connection` bağlantıda gerçek `SELECT 1` çalıştırıp gecikmeyi
  ölçecek. Sahte bağlantıyla davranış test edildi; gerçek PostgreSQL bağlantısı
  kuruluma kadar tamamlanmış sayılmayacak.
- `.env.example` yalnız `CHANGE_ME` örneği içeriyor; gerçek `.env` Git dışında.
- Beş yeni testle toplam 83 Python testi geçti; Ruff kontrolleri temiz.

D1 henüz tamamlanmadı. Resmî Windows kurucusu ve Python veritabanı paketleri
kullanıcının indirme onayından sonra kurulacak; ardından gerçek bağlantı ve
yanlış parola testi yapılacak.

## 9 Kasım 2026 — İlk panel ekran görüntüsü README'ye eklendi

- V3'ün daha önce eksik kalan kalıcı ekran görüntüsü görevi tamamlandı.
- FastAPI ve Vite yalnız çekim süresince yerel olarak çalıştırıldı; kurulu
  Microsoft Edge başsız modda doğrudan `127.0.0.1:5173` adresini görüntüledi.
- 1440×1000 PNG görsel `docs/images/isg-kontrol-paneli.png` olarak kaydedildi ve
  görsel olarak kontrol edildi.
- Panel uygulama sunucusunu `Çalışıyor`; henüz API sürecine bağlanmayan analiz
  motoru ve PostgreSQL'i `Bağlı değil`; kamera kaynağını `0` gösteriyor.
- Görüntüde kamera karesi, çalışan bilgisi veya başka kişisel veri bulunmuyor.
- README'deki çalıştırma adreslerinin altına görsel ve dürüst durum açıklaması
  eklendi. V1–V3 erken arayüz bölümü artık tamamlandı.

## 10 Kasım 2026 — D2 veritabanı şema sözleşmesi hazırlandı

- SQLAlchemy ve Alembic koduna geçmeden önce kalıcı kayıtların sınırları
  `docs/VERITABANI_SEMASI.md` belgesinde kesinleştirildi.
- Kamera, kamera oturumu, çalışan, değiştirilemez kural sürümü, olay, ekipman
  bulgusu, medya ve eklemeli inceleme geçmişi için alanlar belirlendi.
- Kamera veya çalışan pasifleştirildiğinde eski olayların korunması; geçmiş kural
  sürümünün değişmemesi; tanınmayan kişinin bir çalışana zorla bağlanmaması ve
  medya silinse de olay kaydının kalması şema kuralı haline getirildi.
- UUID kimlikleri, UTC zamanları, JSONB kural anlık görüntüsü, önemli indeksler,
  yabancı anahtar/silme davranışları ve ilk migration sırası belgelendi.
- Bu çalışma indirme yapmadı. D2 henüz tamamlanmadı; SQLAlchemy/Alembic paketleri
  ile gerçek PostgreSQL yükseltme–geri alma deneyi kullanıcı onayından sonra
  yapılacak.

## 10 Kasım 2026 — PostgreSQL gerçek bağlantısı tamamlandı (D1)

- Kullanıcının Wi-Fi ve indirme onayından sonra WinGet üzerinden yayıncısı
  PostgreSQL Global Development Group olan PostgreSQL 18.6 paketi indirildi;
  paket SHA-256 özeti kurulumdan önce doğrulandı.
- EDB kurucusunun Windows Türkçe bölge adındaki ASCII dışı karakter nedeniyle
  başlatamadığı boş küme, PostgreSQL'in kendi `initdb` aracıyla UTF-8 ve ICU
  `tr-TR` ayarında güvenli biçimde oluşturuldu.
- Yönetici gerektiren Windows servisi yerine geliştirmeye uygun kullanıcı süreci
  seçildi. `PROJEYI_BASLAT.cmd` artık PostgreSQL + FastAPI + React'i birlikte
  başlatıyor; `PROJEYI_DURDUR.cmd` üçünü de kontrollü kapatıyor.
- `isg_kamera` veritabanı ve superuser olmayan `isg_app` rolü oluşturuldu.
  Parolalar Windows kullanıcı ortamına kaydedildi; Git çalışma ağacına girmedi.
- SQLAlchemy 2.1.8, Alembic 1.20.1 ve Psycopg 3.3.8 kuruldu; sürümler
  `requirements-database.lock.txt` içinde sabitlendi.
- Proje koduyla gerçek `SELECT 1` geçti. Bilerek yanlış parola ve kontrollü kapalı
  sunucu bağlantısı reddedildi; yeniden başlatma sonrası sonuç tekrar `ok` oldu.
- Kapalı sunucuda uzun varsayılan bekleme gözlendiği için bağlantı zaman aşımı
  ayarlanabilir 5 saniyeye indirildi.
- Health API ve panel veritabanını artık gerçek bağlantıya göre `Bağlı`,
  `Ulaşılamıyor` veya `Ayarlanmamış` olarak gösteriyor; hata ayrıntısı/parola
  kullanıcıya sızdırılmıyor.
- Başlatıcı uçtan uca denendi: health yanıtı `database: ok`, panel HTTP 200 verdi.
  README ekran görüntüsü gerçek bağlı PostgreSQL durumuyla yenilendi.
- Toplam 85 Python testi geçti. Ruff, ESLint, TypeScript kontrolü ve Vite üretim
  derlemesi temiz sonuç verdi.

D1 tamamlandı. Sıradaki görev D2: SQLAlchemy modelleri ve ilk Alembic migration'ı.

## 10 Kasım 2026 — Çekirdek veritabanı şeması tamamlandı (D2)

- Ortak adlandırma düzenine sahip tipli SQLAlchemy 2 modelleri eklendi: kamera,
  kamera oturumu, çalışan, ekipman kataloğu, değiştirilemez kural sürümü, olay,
  olay bulgusu, medya ve eklemeli inceleme geçmişi.
- Kimlik sonucu ile çalışan bağlantısının tutarlılığı, olay zaman sırası, tek güncel
  kural, hazır medya dosya bilgileri ve geçmiş kayıt silme koruması doğrudan
  PostgreSQL kısıtlarıyla güvenceye alındı.
- İlk Alembic migration'ı `20261110_0001` oluşturuldu. Sabit katalogdaki baret,
  reflektif yelek, eldiven, koruyucu gözlük ve iş botu aynı migration ile eklendi.
- Gerçek PostgreSQL 18.6 üzerinde ilk upgrade geçti. `alembic check` model ile
  şema arasında yeni işlem bulmadı.
- Geçerli kayıt grafiği ve dört kritik reddetme senaryosu
  `scripts/verify_database_schema.py` ile transaction içinde sınandı; deneme
  kayıtları kalıcı bırakılmadı.
- `downgrade base` şemayı temiz kaldırdı; yeniden `upgrade head` ve ikinci şema
  doğrulaması geçti.
- `PROJEYI_BASLAT.cmd`, API başlamadan önce bekleyen Alembic migration'larını
  uygulayacak şekilde güncellendi.
- Başlatıcı boş şema durumunda ayrıca denendi; migration'ı `20261110_0001 (head)`
  seviyesine getirdi, health `database: ok` ve panel HTTP 200 döndürdü.
- Toplam 90 Python testi geçti; Ruff kod ve biçim kontrolleri temiz sonuç verdi.

D2 tamamlandı. Sıradaki görev D3: kullanıcı oturumu, parola özeti, CSRF ve rol
yetkilendirmesi.

## 10 Kasım 2026 — Kimlik doğrulama ve rol güvenliği tamamlandı (D3)

- FastAPI'nin resmî önerdiği `pwdlib 0.3.1` ve Argon2id desteği kuruldu; bağımlı
  sürümler `requirements-security.lock.txt` içinde sabitlendi.
- Parolalar en az 12, en fazla 128 karakter olarak kabul ediliyor ve Argon2id
  (`m=65536, t=3, p=4`) ile tek yönlü özetleniyor. Bu bilgisayardaki tek ölçümde
  özetleme 44,515 ms, doğrulama 43,572 ms sürdü.
- `app_user` ve `user_session` tablolarını ekleyen `20261110_0002` migration'ı
  gerçek PostgreSQL'e uygulandı. Geri almada D2 tabloları ve beş ekipman kaydı
  korundu; yeniden yükseltme ve `alembic check` geçti.
- Cookie, UUID ile 256 bit rastgele doğrulayıcıdan oluşuyor. Veritabanı yalnız
  doğrulayıcının SHA-256 özetini tutuyor; ham oturum veya CSRF belirteci saklanmıyor.
- Oturum cookie'si HttpOnly + SameSite=Strict; ayrı CSRF cookie/header eşleşmesi
  yazma işlemlerinde zorunlu. Yerel HTTP'de Secure kapalı, HTTPS tesliminde açık.
- Oturum için 30 dakika hareketsizlik, 8 saat mutlak süre ve sunucu taraflı iptal;
  giriş için varsayılan beş başarısız denemeden sonra 15 dakika kilit eklendi.
- Admin ve İSG rolleri eklendi. Kullanıcı listeleme/oluşturma/pasifleştirme yalnız
  admin; medya meta bilgisi iki role açık; yetkisiz istekler ayrıntı sızdırmıyor.
- İlk yönetici için parolayı göstermeyen ve komut geçmişine almayan
  `scripts/create_initial_admin.py` eklendi; varsayılan hesap/parola yok.
- Gerçek PostgreSQL + ASGI deneyinde 11 kontrol geçti: yetkisiz medya, cross-origin
  login, yanlış parola, cookie bayrakları, `/me`, CSRF, admin kullanıcı oluşturma,
  ham token saklamama, rol sınırı, logout iptali ve geçici kilit.
- Gerçek Uvicorn başlangıcında health `database: ok`, migration
  `20261110_0002 (head)` oldu; oturumsuz `/auth/me`, `/users` ve `/media/{id}`
  isteklerinin üçü de 401 döndürdü. Test sonunda bütün süreçler kapatıldı.
- Toplam 101 Python testi, Ruff ve `pip check` temiz sonuç verdi.

D3 tamamlandı. Sıradaki görev D4: kamera, çalışan ve sürümlü kural yönetimi API'leri.

## 10 Kasım 2026 — Kamera, çalışan ve kural yönetimi tamamlandı (D4)

- Yönetici ve İSG rollerine açık kamera listeleme, ayrıntı, ekleme, düzenleme ve
  pasifleştirme API'leri yazıldı. Fiziksel silme ucu eklenmedi.
- Webcam kaynağında cihaz numarası, isteğe bağlı çözünürlük ve FPS sınırlandı.
  Kayıtlı video yalnız göreli, üst klasöre çıkmayan ve desteklenen uzantılı yol
  kabul ediyor.
- Gerçek RTSP kamera ve güvenli kimlik kasası doğrulanmadığı için RTSP URL/parola
  kabul edilmiyor; gizli bilgi `source_config` içine yazılmıyor.
- Çalışan numarası benzersiz ve normalize; ad, bölüm ve aktiflik alanları için
  ekleme, düzenleme, listeleme ve pasifleştirme uçları eklendi.
- Sabit beş ekipman kataloğu okunabiliyor. Kamera temel ekipmanı ile en fazla 32
  bölge ve bölge başına 3–50 normalize nokta kabul eden kural isteği yazıldı.
- Çokgenlerde 0–1 koordinat, tekrar eden nokta, sıfır alan ve kendi kendini kesme
  denetleniyor. Bölge kimlikleri ve ekipman seçimleri yinelenemiyor.
- Kural değişikliği eski satırı ezmiyor: güncel sürümün bitiş zamanı kapanıyor ve
  kamera satırı kilitlenerek artan numaralı yeni sürüm oluşturuluyor.
- `20261110_0003`, geçmişteki bir tanıma A → B → A biçiminde dönebilmeyi sağladı.
  Aynı etkin tanım yine `409` ile reddediliyor.
- Gerçek PostgreSQL + ASGI deneyinde sekiz kontrol geçti: yetkisiz yönetim,
  güvensiz kaynak, gizlisiz kamera, çalışan normalizasyonu, geçersiz çokgen,
  olayın tarihsel kuralı, eski tanıma dönüş ve pasifleştirme.
- Migration geri alma/yükseltme ve `alembic check` geçti. Deneme kayıtları
  temizlendi, PostgreSQL kapatıldı.
- Toplam 116 Python testi ve Ruff kontrolü temiz sonuç verdi.

D4 tamamlandı. Sıradaki görev D5: çalışan arama, pasifleştirme ve geçmiş sorguları.

## 10 Kasım 2026 — Çalışan arama ve geçmiş sorguları tamamlandı (D5)

- `GET /api/v1/employees` isteğine ad, çalışan numarası veya bölümde arayan `q`,
  en fazla 100 kayıtlık `limit` ve negatif olamayan `offset` parametreleri eklendi.
- Arama metnindeki `%`, `_` ve ters bölü LIKE jokerine dönüşmeden güvenle
  kaçırılıyor. Sonuçlar önce ad, sonra benzersiz çalışan numarasıyla sıralanıyor.
- `GET /api/v1/employees/{id}/events`, yalnız yüz tanıma tarafından o çalışana
  bağlanmış olayları kamera adı, kural sürümü, inceleme durumu ve ekipman
  bulgularıyla döndürüyor.
- `GET /api/v1/employees/{id}/history-summary`, toplam, bekleyen, doğrulanmış,
  yanlış alarm ve son olay zamanını ayrı alanlarda veriyor.
- Pasifleştirme fiziksel silme yapmıyor. Varsayılan çalışan listesi pasif kişiyi
  gizliyor; `include_inactive=true` kaydı tekrar gösteriyor ve geçmiş uçları
  pasif çalışan için çalışmaya devam ediyor.
- Olayı elle bir çalışana bağlayan uç eklenmedi; geçmiş yalnız otomatik
  `employee_id` bağlantısını okuyor.
- Gerçek PostgreSQL + ASGI deneyinde aynı tam ada sahip iki çalışan farklı
  numaralarıyla arandı. Bir kişiye biri bekleyen biri doğrulanmış iki olay ve
  baret bulgusu bağlandı; özet doğrulandı.
- Aynı kişi pasifleştirildikten sonra etkin listeden çıktı, tüm kayıt listesinde
  kaldı ve iki olayın ikisi de geçmişte görünmeye devam etti. Geçici kayıtlar
  temizlendi ve PostgreSQL kapatıldı.
- Toplam 117 Python testi, Ruff biçim ve kod kalite kontrolleri temiz sonuç verdi.

D5 tamamlandı. Sıradaki görev E1: tek kötü kare yerine süreli gözlemlerden olay
adayı üretmek.

## 10 Kasım 2026 — Zamansal ihlal-adayı kararı tamamlandı (E1)

- `TemporalViolationTracker`, kanıtı kamera oturumu, kural sürümü, takip numarası
  ve ekipman kodu birleşimine göre ayrı tutacak şekilde eklendi. Böylece başka
  oynatma, kişi, kural veya ekipmanın gözlemleri birbirine karışmıyor.
- Başlangıç politikası 3 saniyelik kayan pencerede en az 4 ihlal-adayı gözlem ve
  ilk–son gözlem arasında en az 1,5 saniye istiyor. İki ihlal gözlemi arasındaki
  azami boşluk 1 saniye.
- Tek kötü kare ve 0,3 saniyeye sıkışan dört kötü kare aday oluşturmadı. 0,0;
  0,5; 1,0 ve 1,5 saniyelerdeki sürekli dört gözlem adayı tam 1,5 saniyede
  oluşturdu.
- 1 saniyeden uzun gözlem arası eski kanıtı sıfırlıyor. Kısa
  `değerlendirilemiyor` dönemi ihlal sayısını artırmadan kanıtı koruyor; uzun
  belirsizlik eski kanıtı düşürüyor.
- `uygun` sonucu birikmiş kanıtı hemen sıfırlıyor. Aday eşiğine geçiş yalnız bir
  kez `became_candidate=true` üretiyor; aynı adayın olay yaşam döngüsü E2'ye
  bırakılıyor.
- Geriye giden/NaN zaman, negatif takip numarası ve tutarsız politika değerleri
  reddediliyor. 10 saniye gözlenmeyen takip belleği temizlenebiliyor; biten kamera
  oturumunun bütün kanıtı açıkça sıfırlanabiliyor.
- `scripts/evaluate_temporal_policy.py`, tek kare, hızlı dört kare, sürekli,
  seyrek, kısa belirsizlik ve uygunlukla sıfırlama olmak üzere altı kontrollü
  senaryoyu JSON olarak ölçtü.
- Eşikler gerçek fabrika doğruluğu iddiası değildir. 5–10 analiz FPS hedefinde
  tek kare alarmını engelleyen ölçülmüş yazılım başlangıcıdır; saha videosuyla
  yeniden kalibre edilmelidir.
- Toplam 130 Python testi ve Ruff biçim/kod kalite kontrolleri geçti.

E1 tamamlandı. Sıradaki görev E2: aynı adayın her karede yeni olaya dönüşmesini
engelleyen olay birleştirme ve bitiş yaşam döngüsü.

## 10 Kasım 2026 — Olay birleştirme ve bitiş yaşam döngüsü tamamlandı (E2)

- `EventLifecycleTracker`, aynı kamera oturumu ve takip numarası için en fazla
  bir açık teknik olay tutacak şekilde eklendi. Aynı takip numarası başka oturumda
  bağımsızdır.
- İlk aday `started` ve `notification_required=true` üretiyor. Devam eden her
  gözlem aynı olay UUID'siyle `updated` oluyor ve tekrar bildirim istemiyor.
- Kesintisiz dönemde eksik ekipman listesi değişirse olay bölünmüyor. O anda
  geçerli ekipmanlar ayrı, olay boyunca görülen bütün ekipmanlar birleşik tutuluyor.
- Tek uygun kare olayı kapatmıyor. En az iki uygun gözlem ve ilk uygun gözlemden
  itibaren en az 1 saniye geçince `resolved` nedeniyle kapanıyor. Bu arada ihlal
  dönerse aynı olay devam ediyor.
- Takip 2 saniye görülmezse `observation_lost`, kamera/video oturumu kapanırsa
  `session_ended`, aynı takipte kural sürümü değişirse `rule_changed` nedeni
  üretiliyor. Kural değişiminde eski olay kapanıp gerekiyorsa yeni olay başlıyor.
- Olay sona erdikten sonra yeni ihlal yeni UUID ve yeni başlangıç bildirimi alıyor.
  Böylece gerçek ayrı dönemler korunurken her karede satır/bildirim çoğalmıyor.
- Geriye giden/NaN zamanlar, negatif takip numarası ve tutarsız süre politikaları
  reddediliyor. Son görüldü zamanı kapanış zamanıyla yanlışlıkla ezilmiyor.
- `scripts/evaluate_event_lifecycle.py` kontrollü sekiz gözlemde iki ayrı olay ve
  iki bildirim başlangıcı üretti; kısa düzelme aynı olayda kaldı, yeterli düzelme
  `resolved` ile bitirdi.
- Bu aşama yalnız geçiş komutlarını üretir. Veritabanına yazma ve gerçek panel
  bildirimi E4'te; fotoğraf/klip kanıtı E3'te eklenecek.
- Toplam 143 Python testi ve Ruff biçim/kod kalite kontrolleri geçti.

E2 tamamlandı. Sıradaki görev E3: olay fotoğrafı ve sınırlı öncesi/sonrası klip
tamponu.

## 11 Kasım 2026 — Fotoğraf ve kısa olay klibi tamponu tamamlandı (E3)

- `EncodedEvidenceFrame`, ham görüntü yerine JPEG olarak sıkıştırılmış kare taşır.
  Varsayılan tampon 5 saniye geçmiş, en fazla 150 kare ve 32 MiB ile sınırlıdır;
  hangi sınır önce aşılırsa en eski kare atılır.
- Olay başladığında olay zamanına en yakın kare fotoğraf seçildi. Önceki 5 saniye
  ile sonraki 5 saniyenin kareleri tek kısa klip işi altında birleştirildi.
- Dosya yazma ve MP4 kodlama ayrı bir iş parçacığına taşındı. Analiz çağrıları
  yazıcıyı beklemiyor; sekiz işlik kuyruk dolarsa olay kanıtı açıkça hatalı oluyor.
- Medya işi `preparing`, `ready` ve `failed` durumlarını taşıyor. Kamera/video erken
  biterse eldeki kareler `session_ended` nedeniyle kısmi klip olarak işaretleniyor.
- Fotoğraf ve klip önce `.part` dosyalarına yazılıp atomik olarak gerçek adlarına
  taşınıyor. Hata halinde yarım dosyalar temizleniyor; var olan olay dosyalarının
  üzerine yazılmıyor. Boyut ve SHA-256 özeti sonraki veritabanı kaydına hazır.
- 12 yeni birim testi bellek sınırı, zaman penceresi, yavaş/hatalı yazıcı, dolu
  kuyruk, kısmi klip, yarım dosya temizliği ve üzerine yazmama kuralını doğruladı.
- Gerçek OpenCV deneyinde 7 karelik MP4 üretildi. 3.377 bayt fotoğraf ve 6.789 bayt
  klip dosyası oluştu; klip tekrar açıldığında 7 karenin tamamı çözüldü.

E3 tamamlandı. Sıradaki görev E4: olayı ve medya durumlarını PostgreSQL'e kalıcı
yazmak, ardından yeni/değişen olayları WebSocket üzerinden panele bildirmek.

## 11 Kasım 2026 — Kalıcı olay ve yeniden bağlanabilir bildirim tamamlandı (E4)

- E2 geçişlerini kamera oturumu kaynak zamanından UTC'ye çevirip `safety_event`,
  `event_finding` ve iki hazırlık medya kaydına yazan `event_store.py` eklendi.
- Aynı olay başlangıcının tekrar oynatılması idempotent yapıldı. Aynı UUID'nin
  farklı kamera, takip, kural, kişi veya model sürümüyle kullanılması reddediliyor.
- E3 kanıt sonucu hazır olduğunda fotoğraf/klip yolu, türü, boyutu ve SHA-256 özeti;
  hatalı olduğunda görünür hata durumu kalıcı medya satırlarına uygulanıyor.
- Her olay için bir fotoğraf ve bir klip kuralı veritabanı benzersizliğiyle korundu.
- Artan kimlikli `event_change` tablosu eklendi. Başlangıç, önemli güncelleme,
  bitiş, medya hazır ve medya hatalı değişiklikleri bağlantıdan bağımsız saklanıyor.
- Yetkili olay listesi ile `after_id` tabanlı değişiklik listesi eklendi. WebSocket
  aynı imleçten yaklaşık saniyelik sorguyla devam ediyor ve yalnız admin/İSG
  oturumlarını kabul ediyor.
- Gerçek PostgreSQL deneyinde panel yokken olay commit edildi; değişiklik sırası
  `started → updated → ended → media_ready` oldu. Panel sonradan açılınca olay
  listede bulundu ve WebSocket son kaçırılan değişikliği aldı.
- İleri migration başarıyla uygulandı. Veri silebileceği için geliştirme veritabanında
  otomatik downgrade çalıştırılmadı. Geçici deney kayıtları temizlendi.
- Toplam 156 Python testi, Ruff kontrolleri ve bağımlılık denetimi geçti.

E4 tamamlandı. Sıradaki görev E5: inceleme sonucu, açıklama ve düzeltilebilir ama
silinmeyen inceleme geçmişi.

## 11 Kasım 2026 — İnceleme kararı ve düzeltme geçmişi tamamlandı (E5)

- Olay için `pending`, `confirmed` ve `false_alarm` insan inceleme kararları API'ye
  eklendi. Teknik olay durumu ile insan kararı ayrı tutulmaya devam ediyor.
- Her karar en az iki karakterlik normalleştirilmiş açıklama, kararı veren kullanıcı,
  önceki/yeni durum ve artan revizyon numarasıyla `event_review_revision` tablosuna
  ekleniyor. Önceki revizyonlar güncellenmiyor veya silinmiyor.
- Olay satırı karar işlemi boyunca kilitlenerek eşzamanlı kararların aynı revizyon
  numarasını kullanması engellendi. Güncel karar hızlı listeler için olayda tutuluyor.
- Karar yazma geçerli admin/İSG oturumuna ve CSRF doğrulamasına bağlandı. Her karar
  E4 değişiklik akışına durum ve revizyon numarası ekleyerek paneli güncelleyebilir.
- Gerçek PostgreSQL deneyinde CSRF'siz istek reddedildi. Ardından
  `pending → confirmed → false_alarm` iki ayrı revizyon olarak okundu ve olay listesi
  son durumu yanlış alarm gösterdi; ilk karar denetim geçmişinde korundu.
- Çalışan özet sorgusu yalnız güncel `confirmed` olayları doğrulanmış ihlal saydığı
  için `false_alarm` kararı bu sayıyı artırmıyor.

E1–E5 olay üretimi ve kanıt aşaması tamamlandı. Sıradaki öncelik F1: mevcut React/
TypeScript panelini gerçek oturum ve olay API'lerine bağlayarak giriş ekranını kurmak.

## 11 Kasım 2026 — Web paneli giriş ve korumalı yönlendirme tamamlandı (F1)

- React uygulamasına merkezi `AuthProvider` eklendi. Açılışta `/auth/me` ile gerçek
  sunucu oturumu kontrol ediliyor; 401 ile sunucu bağlantı hatası ayrılıyor.
- Kullanıcı adı/parola formu ve bağlantı hatasında yeniden deneme davranışı eklendi.
  Parola tarayıcı kalıcı depolamasına yazılmıyor.
- Genel bakış, kamera, olay ve çalışan rotaları `RequireAuth` arkasına alındı.
  Kullanıcı girişten sonra başlangıçta istediği korumalı yola geri dönebiliyor.
- Üst çubukta kullanıcının adı ve admin/İSG rolü gösteriliyor. Çıkış yerel HTTP ve
  ileride HTTPS için iki CSRF cookie adını destekliyor; hata kullanıcıya bildiriliyor.
- Giriş ekranı mevcut lacivert/kehribar güvenlik merkezi tasarımıyla ve mobil kırılım
  noktalarıyla hazırlandı.
- ESLint, katı TypeScript kontrolü ve Vite üretim derlemesi geçti. Gerçek PostgreSQL
  deneyinde giriş, `/auth/me`, rol, CSRF, güvenli cookie, çıkış ve hesap kilidi dahil
  11 güvenlik kontrolü başarıyla tamamlandı.
- Vite yalnız 571 kB ana JavaScript paketi için performans uyarısı verdi. İşlevsel
  hata yok; sayfalar büyüdükçe dinamik rota yükleme değerlendirilecek.
- Gömülü tarayıcı aracı Edge adresini doğrulayamadığı için otomatik görsel QA
  durduruldu. Geçici test hesabı silindi ve test süreçleri kapatıldı.

F1 tamamlandı. Sıradaki görev F2: gerçek kamera listesini API'den göstermek, kamera
ayrıntısını ve analizi çoğaltmayan ortak önizleme sözleşmesini hazırlamak.

## 11 Kasım 2026 — Kamera listesi, ayrıntısı ve ortak önizleme tamamlandı (F2)

- Kamera sayfası `include_inactive=true` ile gerçek API verisini okuyor; yüklenme,
  hata, boş liste, etkin ve pasif kamera durumlarını ayrı gösteriyor.
- Kamera kartları kaynak türünü ve yalnız güvenli kaynak özetini gösterip UUID tabanlı
  ayrıntı rotasına açılıyor. Ayrıntı sayfasında kaynak ve önizleme durumu var.
- Kamera başına tek JPEG son kare tutan `FilesystemPreviewStore` eklendi. Analiz
  atomik geçici dosya üzerinden yayınlıyor; tarayıcı aynı hazır dosyayı okuyor.
- Önizleme `unavailable`, `live` ve `stale` durumlarını taşıyor. Varsayılan üç
  saniyeyi geçen kare gösterilmeye devam ediyor fakat belirgin biçimde eski işaretleniyor.
- Önizleme durum API'si ve yetkili JPEG API'si eklendi. Cevap önbelleğe alınmıyor;
  yakalama zamanı ve güncellik başlıklarla da bildiriliyor.
- 8 depo testi ile kamera sözleşme testleri geçti. Gerçek PostgreSQL deneyinde kamera
  listelendi; kare yok/live/stale geçişleri ve JPEG bütünlüğü doğrulandı. Tarayıcı
  isteğinin analiz başlatmadığı açıkça sınandı.
- Frontend ESLint ve katı TypeScript kontrolü geçti. Otomatik görsel QA, aynı tarayıcı
  erişim kısıtı nedeniyle yapılamadı.

F2 tamamlandı. Sıradaki görev F3: kamera ayrıntısında çokgen bölge çizme, düzenleme
ve sürümlü ekipman kurallarını gerçek API'ye bağlamak.

## 11 Kasım 2026 — Kamera bölge kural editörü tamamlandı (F3)

- Kamera ayrıntısına genel ekipman şartları ve görüntü üzerinde çokgen bölge çizimi eklendi.
- Bölgeler eklenebiliyor, yeniden düzenlenebiliyor ve kaldırılabiliyor; son nokta geri
  alınabiliyor veya çizim temizlenebiliyor.
- Görüntünün doğal en-boy oranı kullanıldığı için boş kenar koordinat kayması önlendi.
- Noktalar çözünürlükten bağımsız `0–1` aralığında saklanıyor.
- Kesişen, sıfır alanlı, tekrarlı veya üçten az noktalı şekiller arayüzde ve API'de reddediliyor.
- Kayıt eski kuralı ezmiyor; yeni sürüm oluşturuyor ve olay geçmişi korunuyor.
- ESLint, TypeScript, üretim derlemesi, 6 geometri kontrolü ve gerçek PostgreSQL akışı geçti.

F3 tamamlandı. Sıradaki görev F4: olay listesi, filtreler, canlı bildirim ve fotoğraf/video
inceleme ekranını gerçek olay API'sine bağlamak.

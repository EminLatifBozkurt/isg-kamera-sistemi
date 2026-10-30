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

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

Bu adımın değişiklikleri yerel çalışma klasöründe hazırlandı; GitHub'a gönderim
ve commit işlemi yapılmadı.

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

# İSG kamera projesi — teknoloji seçimi

İlk araştırma: 26 Ekim 2026. Bu belge teknoloji seçimlerinin gerekçelerini kaydeder. Güncel uygulama durumu README, ILERLEME.md ve GOREVLER.md içindedir; aşağıdaki öneriler tüm bileşenlerin kurulmuş veya doğrulanmış olduğu anlamına gelmez.

## Donanım

Kullanıcının bildirdiği: Acer Nitro 5, 12. nesil Intel i5, 32 GB RAM, 512 GB SSD. Yerel nvidia-smi sorgusu: NVIDIA GeForce RTX 3050 Ti Laptop GPU, 4096 MiB VRAM, sürücü 610.62. Eğitim ve çıkarım için başlangıç önerisi nano boyutlu model, 640 piksel giriş ve bellek ölçümüne göre küçük batch. Bunlar garanti edilen performans değerleri değildir. İlk deney bir kaynakla yapılacak, iki kaynağa ancak ölçüm sonrasında geçilecek.

## Önerilen yığın

| Katman | Seçim | Gerekçe |
|---|---|---|
| Görüntü işleme ve sunucu dili | Python 3.12 | Modeli eğiten, videoyu işleyen ve sunucuyu çalıştıran kodlar Python ile yazılacak; sürüm uyumluluğu kurulumda sınanacak |
| Model çalıştırma ve eğitim | PyTorch, NVIDIA CUDA destekli paket | Yerel NVIDIA GPU kullanımı; paket/sürücü uyumu doğrulanacak |
| Nesne tespit modeli | Ultralytics YOLO26n, PPE verisiyle ince ayar | Yeni proje için küçük ve güncel başlangıç; YOLO11n karşılaştırma alternatifi |
| Kişi takibi | ByteTrack | Kamera içi geçici takip; çalışan kimliği veya kameralar arası kimlik değildir |
| Video ve görüntü | OpenCV + FFmpeg | Webcam, dosya, ağ akışı okuma; klip üretme ve tarayıcıya uygun kodlama |
| Sunucu | FastAPI + Pydantic + Uvicorn | Veri doğrulama, API belgeleri, WebSocket desteği |
| Ön yüz | React + TypeScript + Vite | Etkileşimli yerel panel, tip kontrolü, derlenmiş statik arayüz |
| Arayüz bileşenleri | Material UI ücretsiz çekirdek bileşenleri | Formlar, tablolar, iletişim kutuları; ücretli bileşen gereksinimi yok |
| Sayfa yönlendirme | React Router | Kamera, olay ve çalışan sayfaları |
| Bölge çizimi | react-konva / Konva | Kamera görüntüsünde çokgen çizme ve düzenleme |
| Bölge hesabı | OpenCV pointPolygonTest | İlk sürüm için ayrı coğrafi veritabanına ihtiyaç olmadan nokta/çokgen testi |
| Kalıcı kayıt | PostgreSQL | Çalışan, olay, kamera, kural ve inceleme ilişkileri |
| Veritabanı erişimi | SQLAlchemy 2 + psycopg | Python üzerinden açık veri modelleri ve ilişkiler |
| Şema değişiklikleri | Alembic | Veritabanı yapısının sürümlenmesi |
| Canlı bildirim | WebSocket + veritabanında olay kaydı | Paneli yenilemeden uyarı; kopma sonrası olayları yeniden getirme |
| Canlı önizleme | İlk sürümde sınırlı FPS MJPEG | Basit demo; bant genişliği yüksek, ölçekli kullanım için WebRTC yeniden değerlendirilecek |
| Medya | Yerel dosya sistemi, MP4/JPEG | Veritabanında dosya yolu ve meta bilgiler; disk kotası ve saklama süresi |
| Etiketleme | Gerektiğinde CVAT Community | Kendi fotoğraf/video verilerini etiketleme |
| Oturum | Sunucuda tutulan oturum, HttpOnly çerez | Aynı kaynaktan çalışan panel için basit giriş/çıkış; CSRF, parola özeti ve rol kontrolü uygulanacak |
| Test | pytest, temel panel akışlarında Playwright | Kural mantığı, olay birleştirme, çalışan eşleştirme ve inceleme doğrulaması |
| Kod düzeni | Ruff, ESLint, TypeScript kontrolü | Hataları erken bulma, tutarlı kod |
| Kod yönetimi | Git + GitHub, tek depo | Arayüz, sunucu, analiz ve belgelerin birlikte sürümlenmesi |
| Çalıştırma | Geliştirmede Windows üzerinde yerel süreçler | GPU ve webcam erişimini başlangıçta kolay tutma |
| Paketleme | Sonraki aşamada Docker Compose | Tekrarlanabilir kurulum; GPU/Windows kamera geçişi ayrıca sınanacak |

## Alternatifler ve seçim nedenleri

- C++ performans odaklı bileşenlerde güçlüdür ancak bu aşamada geliştirme ve öğrenme yükünü artırır. Node.js, C# ve Java ile sunucu yapılabilir; model tarafında yine Python gerekeceğinden ilk sürümde ikinci sunucu dili seçilmedi.
- Django yönetim ve iş uygulamalarında güçlü bir alternatiftir. Burada özel kamera ekranları ve Python analiz bileşeniyle API iletişimi ön planda olduğu için FastAPI öneriliyor. Flask ile aynı şeyler yapılabilir, ancak doğrulama ve API belgelerini daha fazla birleştirmek gerekir.
- Next.js kullanılabilir; arama motoru görünürlüğüne veya sunucuda sayfa üretimine ihtiyaç olmayan yerel panelde Vite ile React daha dar bir başlangıç sunar. Vue da geçerli alternatiftir; React ekosistemi ve Konva entegrasyonu tercih sebebidir.
- SQLite kısa bir prototip için yeterli olabilir; hedeflenen eşzamanlı olay yazımı ve inceleme nedeniyle baştan PostgreSQL öneriliyor. MongoDB yerine ilişkisel kayıtlar ve bütünlük önceliklidir. MySQL de kullanılabilir; PostgreSQL bu proje için tek mümkün seçim değildir.
- BoT-SORT ihtiyaç olursa takip karşılaştırmasına alınabilir. Yüz tanıma, DeepFace ve kimlik yeniden tanıma ilk sürümde gerekli değildir.
- Bulut görüntü analiz API'si veya her kareye büyük dil modeli çağrısı, yerel ve sürekli işleme hedefi için önerilmiyor. TensorRT/ONNX yalnızca ölçüm performans ihtiyacı gösterirse değerlendirilecek.
- Redis, Celery, Kafka ve Kubernetes ilk sürümde gerekli değil. API ile GPU analiz süreci ayrı çalışacak; iletişimin kalıcı olay kaydı üzerinden tasarlanması mimari aşamada netleştirilecek.

## Ekipman ve eğitim kararı

Hazır genel YOLO ağırlıkları özel PPE desteği anlamına gelmez. Başlangıç veri adayı Construction-PPE: 1.416 görüntü, beş ekipman türü (baret, eldiven, yelek, bot, gözlük), kişi ve bazı eksiklik sınıfları. Hazır bir nihai güvenilirlik kanıtı değildir. Veri etiketleri, lisansları ve kamera koşulları incelenecek.

İlk veri destekli aday kapsam: baret, yelek, eldiven, gözlük ve iş botu görünümü. Maske, kulak koruyucu ve emniyet kemeri sabit kataloğa ancak uygun veri ve test bulunursa eklenecek; kullanıcı arayüzünden yeni tür ekleme olmayacak. Botun koruyucu standardı, maskenin filtre niteliği ve kemerin güvenli ankraja bağlanması salt nesne varlığından çıkarılmayacak.

Görünür ekipman ilgili kişiye atanacak; yanındaki kişinin ekipmanı diğerine sayılmayacak. Bulunamayan ekipman doğrudan eksik kabul edilmeyecek. Görünürlük, kişinin boyutu, süre ve eksiklik kanıtı değerlendirilecek; sonuç uygun, ihlal adayı veya değerlendirilemiyor olabilir.

Hazır ağırlık üzerinden ince ayar yapılacak. Veri ayrımı video/kaynak bazında olacak; aynı videonun komşu kareleri eğitim ve teste dağıtılmayacak. Ölçümler: sınıf başına precision/recall, mAP, olay seviyesinde kaçırma ve yanlış alarm, saat başına yanlış bildirim, uçtan uca gecikme, FPS, VRAM, CPU ve disk.

## Uygulama yaklaşımı

Tek depo içinde modüler uygulama, API ve ayrı analiz süreci öneriliyor. Tarayıcı kamerayı her açtığında yeni analiz başlatmayacak. CPU/GPU işi web istek döngüsünü engellemeyecek. Kamera başına sınırlı kuyruk ve zaman damgası kullanılacak; görüntü gecikerek birikmeyecek. İlk ölçüm hedefi tek kaynak ve ayarlanabilir 5–10 analiz karesi/saniye olabilir; ölçülmüş performans veya güvenlik garantisi değildir.

Bölge noktaları çözünürlükten bağımsız oranlarla kaydedilecek. İlk yaklaşım kişinin kutusunun alt orta noktasını zemindeki konumu olarak kullanır; örtülme ve perspektif hataları sınanır. Kamera/bölge kuralları ve olay anındaki sürümleri kaydedilecek. Kişisel ek gereksinimler yalnızca kişi eşleştirmesi varsa otomatik değerlendirilebilir; bilinmeyen kişi için kamera/bölge kuralları çalışır.

Olay kaydı önce kalıcı hale gelecek, sonra bildirim yapılacak. Kısa öncesi/sonrası klip için sınırlı tampon tutulacak. Tek olay sürekli yeni bildirim üretmeyecek. Klip hazır değilse durumu arayüzde belirtilecek. Sürekli tüm kamera arşivi tutulmayacak. Kamera kesintisi ayrı sistem uyarısıdır, ekipman ihlali değildir.

512 GB diskte süreli medya saklama, kota, boş alan uyarısı ve tutarlı silme gerekli. Veritabanı yedeğiyle medya yedeği birlikte düşünülmeli. Medya erişimi oturum ve yetki kontrolünden geçecek; görüntüler herkese açık klasörde sunulmayacak. Çalışma sırasında zorunlu bulut bağlantısı veya CDN kullanılmayacak; ilk kurulum ve indirmeler internet gerektirebilir.

## Lisans kararı

Ultralytics AGPL-3.0 ve Enterprise seçeneklerini sunuyor. Üreticinin lisans açıklaması açık kaynak akademik çalışma ile kapalı şirket kullanımını ayırıyor. Öneri: açık kaynak bitirme projesi için AGPL koşullarına uygun geliştirme. Depo görünürlüğü ve lisans kullanıcıyla ayrıca kesinleştirilecek; şu an depo yayımlanmadı. Kapalı şirket ürünü hedeflenirse lisans/model/veri seçimi yeniden incelenecek. FFmpeg derlemesinin etkin bileşenlerine göre LGPL/GPL koşulları değişebilir; kullanılan derleme kaydedilecek.

## Resmî kaynaklar

- https://docs.ultralytics.com/models/yolo26/
- https://docs.ultralytics.com/models/yolo11/
- https://docs.ultralytics.com/datasets/detect/construction-ppe/
- https://docs.ultralytics.com/modes/track/
- https://www.ultralytics.com/license
- https://pytorch.org/get-started/locally/
- https://fastapi.tiangolo.com/features/
- https://fastapi.tiangolo.com/advanced/websockets/
- https://react.dev/learn/creating-a-react-app
- https://vite.dev/guide/static-deploy
- https://mui.com/material-ui/getting-started/
- https://konvajs.org/docs/react/Transformer.html
- https://docs.opencv.org/4.x/dc/d48/tutorial_point_polygon_test.html
- https://opencv.org/reading-and-writing-videos-using-opencv/
- https://www.postgresql.org/docs/current/datatype-json.html
- https://docs.sqlalchemy.org/en/20/orm/
- https://alembic.sqlalchemy.org/en/latest/
- https://docs.cvat.ai/docs/products/community/
- https://www.ffmpeg.org/legal.html
- https://docs.docker.com/compose/

# Sıralı uygulama görevleri

Her aşama küçük bir teslimle biter. Kullanıcıyla aşama aşama ilerle; bu listenin
tamamını tek seferde uygulama. `[x]` gerçekten tamamlandı, `[ ]` henüz yapılmadı.
Tespit başarısı ve hız için burada sonuç uydurulmaz.

## A. Proje temeli — ilk uygulama adımı

- [x] A1. Yerel deponun doğru GitHub adresine bağlı ve başlangıçta temiz olduğunu doğrula.
  Çıktı: doğrulanan çalışma klasörü ve AGPL-3.0 lisansı.
- [x] A2. Gereksinim ve mimari belgelerini depoya taşı; kapsam kararlarını güncelle.
  Çıktı: kararlar, teknoloji araştırması, tasarım ve bu görev listesi.
- [x] A3. Sunucu paket yapısını, örnek ortam ayarlarını ve Git dışı tutulacak dosyaları ekle.
  Çıktı: Python 3.12 için kurulabilir sunucu paketi; şifre/video/model dosyaları dışarıda.
- [x] A4. Kamera temeli ve aktif bölgelerin şartlarını birleştiren kural kodunu ekle.
  Çıktı: zorunlu olmayan ekipmanda ihlal üretmeme, belirsizliği eksik saymama.
- [x] A5. Ayrı sanal ortamda kurulum yap; test, kod kontrolü ve gerçek HTTP isteğiyle doğrula.
  Bitme ölçütü: testler geçer; API, model ve veritabanı hazırmış gibi görünmez.
  Sonuç: 5 test geçti; Ruff ve biçim kontrolü temiz; health/OpenAPI gerçek HTTP ile 200 döndü.

## B. Veri ve ilk model deneyi — A tamamlandıktan sonra

- [x] B1. Veri setinin kaynağını, lisansını, sınıflarını ve etiket örneklerini incele.
  Çıktı: kaynak/lisans kaydı, sorunlu etiketler, kesin ilk ekipman adayları.
  Sonuç: Construction-PPE ilk temel deney için seçildi. Arşiv denetimi, sınıf
  dağılımı, etiket sorunları ve alternatiflerle karşılaştırma
  `VERI_SETI_INCELEMESI.md` içinde kaydedildi.
- [x] B2. Kullanılacak demo fotoğraf/video kaynaklarının izinlerini belirle.
  Bitme ölçütü: izinli kaynak listesi; görüntüler Git'e yanlışlıkla eklenmez.
  Sonuç: Construction-PPE test görüntüleri, iki pozitif Pexels video adayı ve
  onaylı kendi canlandırmamız için kurallar `DEMO_GORUNTU_KAYNAKLARI.md`
  içinde kaydedildi. Lisansı belirsiz ve izinsiz kamera görüntüleri dışlandı.
- [x] B3. Sanal ortama uygun GPU destekli PyTorch ve model paketlerini kur.
  Bitme ölçütü: PyTorch GPU'yu görür; küçük tensör işlemi GPU'da tamamlanır.
  Sonuç: PyTorch 2.11.0+cu128, torchvision 0.26.0+cu128 ve Ultralytics
  8.4.194 kuruldu. RTX 3050 Ti üzerinde 2048x2048 matris çarpımı CUDA'da
  tamamlandı; tekrar kullanılabilir kontrol betiği ve sabit sürüm listeleri eklendi.
- [x] B4. Hazır modelle tek görüntüde çıkarımı dene.
  Bitme ölçütü: modelin genel sınıfları ile özel PPE sınıflarının farkı belgelenir.
  Sonuç: Genel YOLO26n, PPE etiketli test görüntüsündeki kişiyi 0,907 güvenle
  buldu; model kataloğunda beş PPE sınıfının bulunmadığı gerçek çıktı üzerinden
  gösterildi. Komut, ağırlık özeti ve sınırlamalar `ILK_MODEL_DENEYI.md` içinde.
- [ ] B5. Veriyi video/kaynak bazında eğitim, doğrulama ve test olarak ayır.
  Bitme ölçütü: aynı kaynağın komşu kareleri eğitim ve teste sızmaz.
- [ ] B6. Küçük PPE modelini hazır ağırlıklar üzerinden eğit ve deney ayarlarını kaydet.
  Çıktı: yeniden üretilebilir eğitim komutu, veri sürümü, ağırlık ve deney kaydı.
- [ ] B7. Ayrılmış test verisinde sınıf başına doğruluk ve yerel hız/belleği ölç.
  Bitme ölçütü: sayısal rapor; başarısız sınıflar açık; sabit ekipman kapsamı kesinleşir.

## V. İlk görünür arayüz — B4 tamamlandıktan sonra

- [ ] V1. React/TypeScript arayüz temelini ve sayfa yönlendirmesini kur.
  Çıktı: tarayıcıdan açılan ana panel, kameralar, olaylar ve çalışanlar menüsü.
- [ ] V2. Gerçek sunucu çalışma durumunu ana panele bağla.
  Bitme ölçütü: sunucu/model/veritabanı durumları hazır değilse açıkça öyle görünür.
- [ ] V3. İlk ekranı çalıştırma komutlarını ve ekran görüntüsünü README'ye ekle.
  Bitme ölçütü: kullanıcı yerel adresten ilerlemeyi görebilir.

Bu erken arayüz, daha sonraki F bölümündeki kamera önizleme, bölge çizimi ve
olay inceleme özelliklerinin temelidir. Hazır olmayan özellikler sahte veriyle
çalışıyor gibi gösterilmeyecek.

## C. Tek görüntü kaynağını işleme — B sonuçları uygun olduğunda

- [ ] C1. Kayıtlı videoyu kaynak zamanına uygun hızda oku; zaman/oturum kimliği tut.
  Bitme ölçütü: video tekrarında eski takipler yeni oturuma taşınmaz.
- [ ] C2. Webcam kaynağı ve kaynak durumlarını ekle.
  Bitme ölçütü: açma, kapatma ve bağlantı hatası açıkça raporlanır.
- [ ] C3. ByteTrack ile kamera içi takip ve kişiye ekipman atamasını ekle.
  Bitme ölçütü: komşu kişinin ekipmanı diğerine sayılmaz; belirsizlik korunur.
- [ ] C4. Sınırlı kare kuyruğu ve analiz süreci durumunu ekle.
  Bitme ölçütü: yavaşlamada eski görüntüler sınırsız birikmez; donma fark edilir.
- [ ] C5. İkinci kaynak ve ağ akışını ölçümlere göre değerlendir.
  Bitme ölçütü: desteklenen eşzamanlı kaynak sayısı gerçek ölçümle belirtilir.

## D. Kalıcı kayıt ve uygulama sunucusu

- [ ] D1. PostgreSQL geliştirme kurulumunu ve bağlantı ayarlarını hazırla.
  Bitme ölçütü: bağlantı doğrulanır; şifre depoya girmez.
- [ ] D2. SQLAlchemy tablolarını ve ilk Alembic şema değişikliğini yaz.
  Çıktı: kamera, oturum, kural sürümü, çalışan, olay, medya ve inceleme kayıtları.
- [ ] D3. Kullanıcı oturumu, parola özeti, CSRF ve yönetici/İSG yetkilerini ekle.
  Bitme ölçütü: yetkisiz işlemler ve medya erişimleri reddedilir.
- [ ] D4. Kamera, çalışan ve kural yönetimi API'lerini doğrulamayla ekle.
  Bitme ölçütü: geçersiz kaynak/şekil reddedilir; eski olayların kural sürümü korunur.
- [ ] D5. Çalışan arama, pasifleştirme ve geçmiş kayıt sorgularını ekle.
  Bitme ölçütü: aynı isimler çalışan numarasıyla ayrılır; geçmiş kayıtlar korunur.

## E. Olay üretimi ve kanıt — C ve D üzerine

- [ ] E1. Kural sonucunu süreli gözlemlerle olay adayına dönüştür.
  Bitme ölçütü: tek kötü kare alarm oluşturmaz; eşikler deneyle belgelenir.
- [ ] E2. Olay birleştirme, bitiş nedeni ve tekrar bildirim engelini yaz.
  Bitme ölçütü: bir olay her karede çoğalmaz; takip/oturum değişimi güvenli ele alınır.
- [ ] E3. Fotoğraf ve sınırlı öncesi/sonrası klip tamponunu ekle.
  Bitme ölçütü: klip hazırlanıyor/hazır/hatalı durumları doğru; işlem analizi kilitlemez.
- [ ] E4. Kalıcı olay/değişiklik kayıtları ve WebSocket bildirimi ekle.
  Bitme ölçütü: panel kapalıyken olay kaydedilir; yeniden bağlantıda liste tamamlanır.
- [ ] E5. İnceleme sonucu, çalışan eşleştirme, açıklama ve değişiklik geçmişini ekle.
  Bitme ölçütü: yanlış alarm doğrulanmış ihlal sayısını artırmaz; düzeltme izlenebilir.

## F. Web paneli — API akışları netleştikten sonra

- [ ] F1. React/TypeScript arayüzünü, sayfa yönlendirmesini ve giriş ekranını kur.
  Çıktı: yerel dosyalardan çalışan, API'ye bağlı temel panel.
- [ ] F2. Kamera listesi, ayrıntısı ve ortak canlı önizlemeyi ekle.
  Bitme ölçütü: tarayıcı açılması yeni GPU analizi başlatmaz; eski kare belirgin görünür.
- [ ] F3. Çokgen çizme, düzenleme ve bölge kurallarını ekle.
  Bitme ölçütü: ölçek/boş kenar koordinatları doğru; geçersiz şekiller reddedilir.
- [ ] F4. Olay listesi, filtreler, bildirim ve fotoğraf/video inceleme ekranını ekle.
  Bitme ölçütü: bildirim doğru olayı açar; medya durumu doğru gösterilir.
- [ ] F5. Çalışan profili, eşleştirme, inceleme sonucu ve not akışını ekle.
  Bitme ölçütü: olay çalışana atanır; yanlış atama düzelir; özetler güncellenir.
- [ ] F6. Genel görünüm, sistem durumları ve saklama ayarlarını ekle.
  Bitme ölçütü: kamera kesintisi, analiz durması ve ekipman ihlali karışmaz.

## G. Bölgeyi analize bağlama ve sistem bütünleştirme

- [ ] G1. Normalize çokgen koordinatları ve kişinin zemin konumu hesabını ekle.
  Bitme ölçütü: görüntü ölçeği değişse de aynı konum aynı bölgeye karşılık gelir.
- [ ] G2. Bölge kesişimi ve sınır titreşimini örnek videolarda sına.
  Bitme ölçütü: kamera temeli + bölgelerin ek şartları doğru; örtülme açıkça ele alınır.
- [ ] G3. Kamera/bölge kural değişikliklerini çalışan analize sürümle uygula.
  Bitme ölçütü: eski olayın kanıtı/kuralı değişmez; yeni kuralın geçerlilik anı nettir.

## H. Dayanıklılık, ölçüm ve teslim

- [ ] H1. Disk kotası, medya saklama süresi, yarım dosya temizliği ve hata uyarıları.
  Bitme ölçütü: silinmiş klip hazır görünmez; disk/veritabanı sorunu sessiz kalmaz.
- [ ] H2. Veritabanı ve medya yedekleme/geri yükleme adımlarını dene.
  Bitme ölçütü: seçilmiş bir olayın kaydı ve kanıtı yedekten açılır.
- [ ] H3. Temel akışları API ve tarayıcı testleriyle doğrula.
  Bitme ölçütü: tasarım belgesindeki kabul senaryoları geçer; erişim kontrolleri sınanır.
- [ ] H4. Farklı kamera koşullarında yanlış alarm, kaçırma, gecikme ve kaynak kullanımını ölç.
  Bitme ölçütü: raporda ölçüm ortamı ve başarısız örnekler açıkça yazılır.
- [ ] H5. Yerel ağ kurulumunu, HTTPS'yi ve gerekirse Docker paketlemesini hazırla.
  Bitme ölçütü: başka yerel bilgisayardan giriş yapılır; yeniden başlatma denenir.
- [ ] H6. README, kullanım kılavuzu, demo senaryosu ve bitirme raporunu tamamla.
  Bitme ölçütü: temiz kurulumdan tekrar edilebilir gösterim; gerçek ölçüm sonuçları.

## Sonraya bırakılanlar

Otomatik yüz/kişi tanıma, kameralar arası kimlik eşleştirme, tehlikeli davranış
analizi, tamamen yasak bölge ve yaklaşma alarmı ayrı kapsam olarak ele alınacak.
Kişiye özel ek ekipman şartları, otomatik kimlik yokken canlı tespit iddiasıyla
sunulmayacak; ilk sürümde insan incelemesine yardımcı profil bilgisidir.

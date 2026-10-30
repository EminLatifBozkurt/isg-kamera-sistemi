# İSG kamera sistemi — ilk sürüm tasarımı

Bu belge, kapsam ve teknoloji araştırmasına dayanan tasarım referansıdır. Güncel uygulama ilerlemesi README, ILERLEME.md ve GOREVLER.md içindedir. Ölçüm gerektiren değerler varsayılan hedeflerdir; test sonucu değildir. Tehlikeli davranış analizi ve otomatik kişi tanıma ilk sürümde yoktur.

## 1. Sistemin çalışacağı yer

Bir ana bilgisayar görüntü analizini, web sunucusunu, veritabanını ve medya kayıtlarını barındıracak. Başlangıçta kullanıcının bilgisayarı bu görevi üstlenecek. İSG görevlisi aynı bilgisayardan veya yerel ağdaki başka bilgisayardan tarayıcıyla bağlanabilecek. Görüntü analizi tarayıcıda çalışmayacak. Panel kapatılsa bile ana bilgisayardaki analiz süreci çalıştığı sürece inceleme ve olay kaydı devam edecek. Ana bilgisayar kapanırsa izleme durur.

İlk kurulumda paket, model ve veri indirmek için internet gerekebilir. Normal çalışma sırasında zorunlu bulut servisi olmayacak. Arayüz dosyaları ve yazı tipleri yerelden sunulacak.

## 2. Ana bileşenler

| Bileşen | Sorumluluk | Teknoloji önerisi |
|---|---|---|
| Web paneli | Kamera izleme, bölge çizimi, çalışanlar, olay inceleme | React, TypeScript, Vite, Material UI, Konva |
| Uygulama sunucusu | Oturum, yetki, ayarlar, olay sorguları, bildirim | Python, FastAPI, Pydantic, Uvicorn |
| Analiz süreci | Görüntü okuma, tespit, takip, kural değerlendirme | Python, PyTorch, YOLO26n, ByteTrack, OpenCV |
| Klip işlemleri | Sınırlı tampon, olay görüntüsü ve video üretimi | FFmpeg; analiz sürecini durdurmayan sınırlı iş kuyruğu |
| Veritabanı | Kalıcı kayıtlar ve değişiklik geçmişi | PostgreSQL, SQLAlchemy, Alembic |
| Medya alanı | Olay fotoğrafları ve kısa videolar | Yerel disk, yetkili sunucu üzerinden erişim |

Tek Git deposu içinde modüller ayrılacak. Web sunucusu ile analiz farklı işletim sistemi süreçleri olacak. GPU modeli ilk sürümde tek analiz süreci tarafından yüklenecek; her tarayıcı bağlantısı veya her API sunucu işçisi ayrı model yüklemeyecek. Kamera sayısı arttıkça gereksinim ölçülerek yeniden değerlendirilecek.

## 3. Görüntüden bildirime akış

1. Etkin kaynağın görüntüsünü al: webcam, kayıtlı video veya desteklenen ağ akışı.
2. Kaynağın durumunu ve görüntünün zamanını kaydet. Kamera başına sınırlı kuyruk kullan; işlenemeyen eski kareler sınırsız birikmesin.
3. Model ile kişileri ve desteklenen ekipmanları tespit et.
4. Kamera oturumu içinde kişileri takip et. Takip numarası çalışan kimliği değildir.
5. Ekipmanı ilgili kişiyle eşleştir. Konum, kişinin ilgili vücut bölgesi ve zamansal tutarlılık değerlendirilsin. Karışık veya örtülü durum belirsiz kalabilsin.
6. Kişinin bulunduğu bölgeyi ve geçerli ekipman kurallarını belirle.
7. Her ekipman için uygun / ihlal adayı / değerlendirilemiyor sonucunu üret.
8. İhlal adayını süre ve tekrar gözlemlerle doğrula; tek kötü kareden bildirim üretme.
9. Kalıcı olay kaydını ve ilk kanıt görüntüsünü oluştur. Kısa klip hazırlanırken durumunu ayrıca belirt.
10. Sunucu yeni kayıtları alıp bağlı panellere bildirir. Bildirim kanalı koparsa olay veritabanında kalır.
11. İSG görevlisi olayı inceler, çalışanla ilişkilendirir, sonucunu ve isteğe bağlı açıklamasını kaydeder.

Analiz süreci ile API arasındaki ilk iletişim kalıcı olay/değişiklik kayıtları üzerinden olacak. API bu kayıtları kısa aralıklarla sorgulayarak WebSocket üzerinden iletecek. Başlangıç sorgu aralığı yaklaşık bir saniye olarak ölçülebilir; bu gerçek ölçülmüş gecikme değildir. Redis ilk sürümde zorunlu değil. WebSocket teslimatı, veritabanı kaydının yerine geçmez. Bağlantı yenilenince panel olay listesini ve değişen kayıtları yeniden sorgular; kayıt kimlikleriyle tekrarları ayıklar.

## 4. Kamera ve bölge kuralları

Her kameranın temel ekipman listesi olacak. Kamera üzerindeki çokgen bölgeler temel listeye ek zorunluluk getirebilecek. İlk sürümde bölge temel kamera zorunluluğunu azaltmayacak. Birden fazla bölge çakışıyorsa gereken ekipmanlar birleştirilecek.

Örnek: Kamera genelinde baret ve yelek zorunlu; makine bölgesinde gözlük eklenmişse o bölgede baret + yelek + gözlük gerekir. Aynı kamera ofis ve üretimi birlikte çekiyorsa kamera temeli boş bırakılıp yalnız üretim bölgesine zorunluluk atanabilir. Böylece ofis kısmında yanlış ihlal oluşmaz.

Bu birleşim kuralı teknik öneridir; farklı muafiyet ihtiyacı çıkarsa açık bir tasarım değişikliği olarak ele alınacak.

Bölgeye giriş tek başına ihlal değildir. Kişinin kim olduğu giriş izni belirlemez. Bölgenin ekipman şartları sağlanıyorsa ekipman ihlali üretilmez. Tamamen yasak alan ve yaklaşma uyarısı sonraki, ayrı kural türleri olabilir.

Çokgen noktaları görüntü genişliği/yüksekliğine oranlanmış koordinatlarla tutulacak. Arayüzdeki boş kenarların veya görüntü ölçeğinin koordinatlara karışması engellenecek. İlk konum yaklaşımı, kişinin tespit kutusunun alt orta noktasıdır. Kamera açısı, kesilmiş ayaklar ve örtülme nedeniyle belirsiz konumlar ayrıca ele alınacak. Sınır üzerinde titreşimi azaltmak için kısa süreli kararlılık kontrolü olacak.

Kamera fiziksel olarak döndürüldüğünde veya görüntü kırpması değiştiğinde bölgeler yeniden doğrulanmalı. İlk sürüm sabit açı varsayar. Bölge düzenlemesi, geçersiz çokgenler ve kendini kesen şekiller için doğrulama içerecek.

## 5. Ekipman kataloğu ve değerlendirilebilirlik

İSG görevlisi ekipman türü ekleyip silmeyecek. Uygulamayla gelen sabit kataloğun desteklenen öğeleri seçilebilecek. Başlangıç veri adayları baret, yelek, gözlük, eldiven ve bot görünümüdür. Kesin sınıflar veri inceleme ve doğrulama deneyinden sonra sabitlenecek; bu belge tüm sınıflarda başarı sözü vermez.

Bir sınıfın model tarafından teknik olarak desteklenmesi, her kamerada değerlendirilebilir olduğu anlamına gelmez. Örneğin el görünmüyorsa eldiven eksik denmeyecek. Eldiven, gözlük ve bot gibi küçük ekipmanların kamera başına deneme ile uygunluğu kontrol edilecek. Yeterli ayrıntı olmayan kamerada o ekipmanın denetimi için uyarı gösterilecek. Model güven puanı doğruluğun garantisi veya doğrudan olasılık olarak sunulmayacak.

Bot görünümünden güvenlik standardı, maske görünümünden filtre uygunluğu, kemerin görünmesinden güvenli ankraj çıkarılmayacak. İleride katalog genişlemesi bir yazılım/model güncellemesi olacak.

## 6. Kişi profili ve olay eşleştirme

İlk sürümde çalışan kaydı ile kameradaki takip kaydı farklı kavramlardır. Çalışan sayfasında ad, çalışan numarası, bölüm, etkinlik durumu ve isteğe bağlı ek ekipman gereksinimleri tutulabilir. Benzersiz çalışan numarası isim benzerliklerini ayırır.

Yeni olay çalışansız oluşabilir. İSG görevlisi çalışanı arayıp olayda açıkça işaretlenen kişiyle eşleştirir. Bir karede başka kişiler bulunması onların da aynı olaya atanmasına yol açmaz. İlk sürümde olayın bir hedef kişi takibi olur; diğer kişiler için gerekiyorsa ayrı olay oluşur.

Eşleştirme değiştirilirse önceki değer, işlemi yapan görevli, zaman ve açıklama geçmişte korunur. Aynı takip numarası başka kamera veya yeni kamera oturumunda aynı çalışan sayılmaz. Takip numarasına dayanarak sonraki olaylar otomatik olarak o çalışana atanmaz.

Kritik sınır: kişi otomatik tanınmadığı için kişiye özel ek ekipman şartları bilinmeyen kişiye canlı uygulanamaz. İlk sürümde bunlar profilde bilgi ve inceleme desteğidir. Canlı otomatik ihlal kontrolünün temeli kamera/bölge kurallarıdır. Sonradan çalışan atamak, olay anındaki kuralı sessizce değiştirmeyecek.

## 7. Olayın iki ayrı durumu

Teknik durum: devam ediyor veya sona erdi. Bu durum görüntü analizinin gözlemlediği ihlal adayının sürekliliğiyle ilgilidir.

İnceleme durumu: inceleme bekliyor, ihlal doğrulandı veya ihlal yok/yanlış alarm. İnceleme kararı kamerada kişinin ekipmanı taktığını kanıtlamaz; teknik durumla karıştırılmaz. Yeterli görüntü yoksa görevli olayı beklemede bırakıp not ekleyebilir. İleride ihtiyaç olursa ayrı değerlendirilemedi sonucu eklenebilir.

Devam eden aynı olay her karede yeni kayıt oluşturmaz. Kamera, kamera oturumu, hedef takip, geçerli kural sürümü ve eksik ekipmanlar dikkate alınır. Geçici görünmezlik ekipman takıldı sayılmaz; belirli bir kayıp zamanından sonra olay gözlem kaybı nedeniyle sona erebilir. Sona erme nedeni saklanır. Ekipman listesi değişimi ve kısa kesintiler için birleştirme politikası testte netleşecek; olayın kanıt geçmişi korunacak.

Görevli not ekleyebilir ve kararını gerekçesiyle düzeltebilir. Çalışan profilinde yalnız doğrulanmış olaylar ihlal sayısına girer. Bekleyen, yanlış alarm ve kimliği belirsiz olaylar ayrı gösterilir. Otomatik ceza veya performans puanı üretilmez.

## 8. Ekran tasarımı

| Ekran | İçerik ve başlıca işlemler |
|---|---|
| Giriş | Kullanıcı oturumu, hata mesajları |
| Genel görünüm | Etkin kamera sayısı, inceleme bekleyenler, kamera kesintileri, son olaylar; sayıların filtre ve zaman aralığı açık |
| Kameralar | Ekle/düzenle, kaynak türü, etkinleştir/durdur, bağlantı durumu |
| Kamera ayrıntısı | Önizleme, kişi/ekipman işaretleri, bölge katmanı, model ve işleme durumu |
| Kamera kuralları | Temel ekipman seçimleri, görüntü üzerinde çokgen çizme/düzenleme, bölgeye ekipman atama, kaydetmeden önce doğrulama |
| Olaylar | Kamera, tarih, bölge, ekipman, inceleme durumu, çalışan/bilinmeyen kişi filtreleri |
| Olay ayrıntısı | Neden, zaman, olayın hedef kişisi, fotoğraf/klip, olay anındaki kural, çalışan atama, not ve inceleme sonucu |
| Çalışanlar | Çalışan ekleme, arama, bölüm, etkin/pasif durumu |
| Çalışan ayrıntısı | Bilgiler, ek gereksinimler, ayrı durumlarda geçmiş olaylar, doğrulanmış olay özeti |
| Sistem ayarları | Desteklenen saklama seçenekleri, disk durumu, yönetici kullanıcı işlemleri, model sürüm bilgisi |

Bildirim olaya götürecek. Olay ekranındaki çalışan bağlantısı kişinin sayfasını açacak. Önizleme ilk sürümde düşük FPS MJPEG olabilir; akış sunucudan alınacak. API, analiz sürecinin en güncel önizlemesini tek kopya üretiminden paylaşacak. Tarayıcıların RTSP'yi doğrudan oynatacağı varsayılmayacak. Klipler tarayıcıda çalıştığı doğrulanmış MP4 biçiminde sunulacak.

## 9. Kalıcı kayıt yapısı

| Kayıt | Önemli bilgiler |
|---|---|
| Kullanıcı ve oturum | Giriş bilgisi, parola özeti, rol, oturum süresi |
| Çalışan | Çalışan numarası, ad, bölüm, etkinlik |
| Kamera | Ad, kaynak türü, korunan bağlantı bilgisi, etkinlik, son durum |
| Kamera oturumu | Başlangıç/bitiş, kaynak türü, yeniden bağlanma/yeniden oynatma kimliği |
| Ekipman tanımı | Sabit kod, görünen ad, model sınıfı ve destek durumu |
| Kural sürümü | Kamera temeli, bölge şekilleri, zorunluluklar, geçerlilik zamanı |
| Çalışan ek gereksinimi | Çalışan, ekipman; ilk sürümde incelemeye yardımcı bilgi |
| Olay | Kamera/oturum, hedef takip, başlangıç/son görülme/bitiş, kaynak video zamanı, kural ve model sürümü, inceleme sonucu |
| Olay bulgusu | İlgili ekipman, gözlemler, değerlendirilebilirlik ve kanıt bilgisi |
| Medya kaydı | Dosya kimliği, tür, boyut, hazırlanıyor/hazır/hatalı/silinmiş durumu |
| İnceleme ve değişiklik geçmişi | Not, karar/kişi değişikliği, görevli, zaman |
| Bildirim değişikliği | Sıralı değişiklik kaydı, olay kimliği, değişiklik türü; yeniden sorgulamayı destekler |
| Kullanıcı okuma kaydı | Hangi olayın kullanıcı tarafından görüldüğü; inceleme sonucu değildir |

Video dosyaları veritabanına gömülmeyecek. Çalışanı pasifleştirmek geçmiş olaylarını silmeyecek. Kamera kaldırmak eski kanıtları ve kural sürümlerini bozmamalı. Tüm model kareleri kalıcı kaydedilmeyecek; olay ve gerekli özet gözlemler saklanacak.

## 10. Zaman, video ve depolama

Olayın oluştuğu saat ile kayıtlı videonun içindeki saniye farklı tutulacak. Kayıtlı video demo kaynağı olarak açıkça işaretlenecek. Video yeniden başlatıldığında yeni oturum olacak; takip ve olay birleştirme durumları sıfırlanacak. Normal oynatma hızı kaynak zamanına göre korunacak. Saatler veritabanında UTC, panelde yapılandırılmış yerel saatle gösterilecek; varsayılan Europe/Istanbul.

Klipte olaydan kısa süre öncesi ve sonrası hedefleniyor. Örnek deney ayarı beş saniye öncesi ve beş saniye sonrası olabilir; çözünürlük ve bellek ölçümünden sonra kesinleşir. Tampon sınırlı ve tercihen sıkıştırılmış olacak; çok sayıda yüksek çözünürlüklü ham kare RAM'de sınırsız tutulmayacak. Aynı olay devam ettikçe sınırsız video büyütülmeyecek; ilk sürüm kısa olay klibi ve süre bilgisini saklayacak. Sürekli kamera arşivi ilk sürümde yok.

Olay bildirimi klibin sonunu beklemek zorunda olmayacak. Fotoğrafla olay açılır, klip hazır olduğunda ekran güncellenir. Kamera koparsa kısa/eksik klip durumu gösterilir. Dosya oluşturma geçici dosya ve tamamlandı işaretiyle yönetilir; çökme sonrası yarım dosyalar toparlanır.

Saklama süresi ve toplam medya kotası ayarlanabilir olacak; başlangıç değerleri boş disk ölçülünce belirlenecek. Medya silindiğinde olay kaydı tutulabilir ve görüntünün süresi dolduğu açıkça yazılır. Disk doluluğu veya yazma hatası sessiz kalmayacak. Veritabanı erişilemiyorsa sistem sağlıklı izleme yapıyormuş gibi görünmeyecek. Veri kaybı olasılığı ve son sağlıklı kayıt zamanı sistem uyarısında belirtilecek. Kalıcı veritabanı kesintisinde kayıpsız çalışma ilk sürüm garantisi değildir.

## 11. Oturum, yetki ve çalışırlık

Başlangıçta yönetici ve İSG görevlisi rolleri yeterli. Yönetici kullanıcı ve kamera/kuralları yönetebilir; İSG görevlisi olayları inceleyip çalışanla eşleştirebilir. Kullanıcının istediği gibi İSG rolüne de kamera/bölge kurallarını düzenleme yetkisi verilecek. Kullanıcı/altyapı ayarları yöneticiye ait kalacak. Değişiklikleri yapan kullanıcı kaydedilecek.

Oturum sunucuda tutulacak; parola düz metin tutulmayacak. Aynı kaynaktan sunulan panel için HttpOnly çerez, CSRF koruması, rol kontrolü ve oturum süresi uygulanacak. Üretim benzeri yerel ağ kurulumunda HTTPS kullanılacak; ilk yerel geliştirme ortamı bundan ayrı. Medya istekleri de yetki kontrolünden geçecek. Kamera şifreleri API yanıtlarına, loglara ve Git deposuna girmeyecek.

Analiz süreci son çalıştığı zamanı bildirecek. Panel yalnız kamera bağlantısını değil analiz güncelliğini de gösterecek; son kare eskimişse görüntü donmuş olarak işaretlenecek. Bağlantı kesilmesi, analiz hatası, model yükleme sorunu ve disk sorunu ekipman ihlalinden ayrı sistem uyarılarıdır. Sınırlı yeniden bağlanma denemeleri ve gecikmeli tekrar kullanılacak.

## 12. İlk kabul senaryoları

1. Aynı video ofis kurallarıyla baret alarmı üretmezken baret zorunlu üretim kurallarıyla değerlendirilebilir eksiklikte olay üretir.
2. Kişi gözlük zorunlu bölgeye girdiğinde bölge kuralı uygulanır; bölge dışında yalnız kamera temeli geçerlidir.
3. İki kişi yan yana olduğunda birinin bareti diğerinin ekipmanı olarak sayılmaz; belirsiz durum kesin ihlal diye sunulmaz.
4. Görüntüde el/baş/ayak seçilemiyorsa ilgili ekipmanın yokluğu otomatik varsayılmaz.
5. Devam eden bir olay panelde sürekli yeni satırlar üretmez; kamera yeniden başladığında eski takip kimliğiyle birleştirilmez.
6. Panel kapalıyken kayıt devam eder; yeniden girişte kaçırılan olaylar listelenir.
7. Çalışansız olay sonradan Ahmet'e atanır; Ahmet'in geçmişinde görülür. Yanlış eşleştirme düzeltilir ve geçmişi korunur.
8. Yanlış alarm çalışanının doğrulanmış ihlal sayısını artırmaz; inceleme düzeltmesi özetlere yansır.
9. Kamera kopması veya analiz durması belirgin uyarı üretir; güncel olmayan görüntü canlı gibi sunulmaz.
10. Klip henüz hazır değilse veya saklama süresi dolmuşsa arayüz doğru durumu gösterir.
11. Kurallar değişse bile eski olayın hangi şartlarla oluştuğu incelenebilir.
12. Yetkisiz kullanıcı olay videosuna doğrudan bağlantıyla erişemez.

Bu senaryolar için veri ve beklenen sonuçlar görev listesinde ayrıntılandırılacak. Model doğruluğu, yanlış alarm oranı ve gecikme için kabul eşikleri ilk veri inceleme ve donanım deneyinden sonra belirlenecek.

## 13. Sonraki aşama

Bu tasarıma dayanan sıralı görev listesi GOREVLER.md içindedir. Temel sunucu ve kural kodundan sonra veri/lisans uygunluğu ile bilgisayarda küçük bir GPU destekli PPE deneyi değerlendirilecek. Modelin destek kapsamı ölçülerek arayüz ve sistem bütünleştirmesi ilerletilecek.

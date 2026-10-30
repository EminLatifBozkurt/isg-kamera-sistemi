# Proje kararları ve çalışma hafızası

## Çalışma biçimi

- Kullanıcı öğrenci; bitirme projesini asistanla birlikte geliştirecek.
- Bir aşamayı tamamla, sonucu açıkla, sonra sonraki aşamaya geç. Tüm projeyi tek seferde yapma.
- En uygun teknolojiyi ihtiyaç, doğruluk, donanım, bakım ve lisansla gerekçelendir.
  Aynı dil veya öğrenme kolaylığı daha iyi teknolojiyi elemek için tek başına gerekçe değildir.
- Kodun önemli bölümlerine Türkçe açıklamalar yaz. Teknik kavramları ilk kullanımda açıkla.
- Gerçekleştirilmemiş eğitim, test veya özellikleri yapılmış gibi raporlama.
- Görev ilerlemesini `GOREVLER.md` içinde güncelle.
- İnternetten paket, veri seti, model ağırlığı veya video indirmeden önce yaklaşık
  boyutu kullanıcıya söyle ve açık onay al. Özellikle mobil bağlantı varsayma.
- Kullanıcı kod değişikliklerini ekranda görmek istiyor. B4 model çıkarımından
  sonra gerçek health API'sine bağlı ilk React arayüzü öne alınacak; hazır
  olmayan model/veritabanı durumu açıkça gösterilecek.

## Depo ve donanım

- GitHub: https://github.com/EminLatifBozkurt/isg-kamera-sistemi
- Doğrulanan yerel depo: `C:\Users\Emin\Documents\GitHub\isg-kamera-sistemi`
- Repo lisansı: AGPL-3.0. Mevcut LICENSE korunur; model/veri lisansları ayrıca incelenir.
- Kullanıcının donanımı: Acer Nitro 5, 12. nesil Intel i5, 32 GB RAM, 512 GB SSD.
- Yerel sürücü sorgusu: RTX 3050 Ti Laptop GPU, 4096 MiB VRAM.
- Windows üzerinde Python 3.12.2 mevcut. Proje paketleri ayrı `.venv` içine kurulacak.
- Doğrulanan model ortamı: PyTorch 2.11.0+cu128, torchvision 0.26.0+cu128,
  Ultralytics 8.4.194 ve OpenCV 5.0.0. RTX 3050 Ti üzerinde CUDA hesabı geçti.

## Kesinleşen kapsam

1. Şirketin kendi ağında çalışan web uygulaması; İSG bilgisayarında bildirimler.
2. Gerçek iş yeri kameralarına erişim yok; webcam ve kayıtlı video ile geliştirme/gösterim.
3. Hedef canlı akış; ileride desteklenen ağ kameraları da bağlanabilecek.
4. Ekipman kataloğu sabit ve baret/yelekten geniş olacak. Arayüzden ekipman türü ekleme/silme yok.
5. Kamera ve kamera görüntüsünde çizilen bölgelere ekipman şartları atanabilecek.
6. Bölgeye giriş tek başına ihlal değil; gerekli ekipmanlar herkes için değerlendirilecek.
7. Çalışan profilleri, geçmiş olaylar, olayın çalışanla elle ilişkilendirilmesi.
8. İSG incelemesi, açıklama ve doğrulandı/yanlış alarm kararı; karar düzeltme geçmişi.
9. Kişi tanınmasa bile olay oluşacak. Otomatik kimlik tanıma zorunlu değil.
10. Otomatik davranış analizi ilk sürüm dışında; sonradan ayrıca değerlendirilecek.

## Tasarım ilkeleri

- Kamera temeli + içinde bulunulan bölgelerin ek şartları. Bölgeler temel zorunluluğu azaltmaz.
- Ofis ve üretim aynı görüntüdeyse temel boş bırakılıp üretim bölgesine şart atanabilir.
- Ekipmanın görünmemesi tek başına eksiklik kanıtı değildir.
- Modelden gelen ekipman ilgili kişiye atanmalı; komşu kişinin ekipmanı karıştırılmamalı.
- Takip numarası çalışan kimliği değildir ve kamera/oturum dışında kimlik yerine geçmez.
- Otomatik kimlik yokken kişisel ek şartlar bilinmeyen kişiye canlı uygulanamaz;
  ilk sürümde profil bilgisi ve insan incelemesine yardımcıdır.
- Bir görüntüdeki ihlal adayı, doğrulanmış olay ve İSG'nin inceleme sonucu ayrı kavramlardır.
- Çalışan özetlerinde bekleyen bildirim ve doğrulanmış ihlal ayrı gösterilir.
- Kamera/analiz/disk arızası ekipman ihlalinden ayrı sistem uyarısıdır.
- İlk model adayları baret, yelek, gözlük, eldiven ve bot görünümüdür; başarı doğrulanmadı.
- Kamera ve model sınırlamaları, değerlendirme yapılamayan durumlar açıkça gösterilecek.

## İlk uygulama adımının sınırı

Sunucu temeli, kural kodu, testler ve görev listesi. Görüntü modeli, canlı kamera,
veritabanı ve arayüz henüz uygulanmıyor. Sonraki adım veri/lisans incelemesi ve
küçük bir GPU destekli model deneyi hazırlığıdır.

Tasarım ve teknoloji belgeleri ilk uygulama öncesindeki önerileri içerir. Güncel
uygulama durumu için README ve işaretlenmiş görev listesi esas alınır.

## Demo görüntü kararı

- Construction-PPE test görüntüleri ilk sabit model deneyi için kullanılabilir.
- Pozitif video testi için lisansı kaydedilmiş iki Pexels videosu adaydır.
- Pexels'teki tanınabilir kişiler ihlal yapan kişi olarak gösterilmeyecek.
- Eksik ekipman demosu, kullanıcının veya onay veren gönüllünün güvenli
  canlandırması olacak; gerçek iş yeri ihlali gibi sunulmayacak.
- Medya dosyaları `data/` altında yerel tutulacak ve GitHub'a gönderilmeyecek.

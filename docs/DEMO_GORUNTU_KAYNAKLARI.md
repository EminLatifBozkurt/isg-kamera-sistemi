# Demo görüntü kaynakları ve kullanım kuralları

İnceleme tarihi: 30 Ekim 2026. Bu belge eğitim verisinden ayrı olarak, uygulama
gösteriminde ve video hattı testlerinde kullanılabilecek fotoğraf/video
kaynaklarını kaydeder. Medya dosyalarının kendisi Git deposuna eklenmez.

## Karar özeti

| Kullanım | Kaynak | Durum |
|---|---|---|
| İlk modelin sabit görüntü testi | Construction-PPE test bölümü | Kullanılabilir; AGPL-3.0 ve atıf kaydı korunacak |
| Pozitif ekipman video testi | Aşağıdaki seçilmiş Pexels videoları | Kullanılabilir; yalnız uygun ekipman/oynatma senaryosu |
| Eksik ekipman canlandırması | Kullanıcının veya gönüllünün kendi kaydı | Açık onayla ve güvenli canlandırmayla kullanılabilir |
| Gerçek iş yeri güvenlik kamerası | Şu an mevcut değil | Yazılı kurum izni ve kişisel veri değerlendirmesi olmadan kullanılmayacak |
| YouTube veya rastgele internet videosu | Lisansı doğrulanmamış | Kullanılmayacak ve indirilmeyecek |
| Yapay üretilmiş görüntü | Arayüz yer tutucusu olabilir | Model doğruluğu ölçümünde gerçek veri yerine kullanılmayacak |

## Construction-PPE görüntüleri

İlk model deneyi ve başarısız örnek incelemesi için indirilen resmî
Construction-PPE arşivinin test görüntüleri kullanılabilir. Arşiv AGPL-3.0
lisansı içeriyor ve kaynak/bütünlük bilgileri `VERI_SETI_INCELEMESI.md` içinde.

Kurallar:

- Ham görüntüler ve türetilmiş videolar `data/` altında, yalnız yerel bilgisayarda tutulur.
- Rapor veya sunumda örnek gösterilirse veri setinin adı ve resmî bağlantısı yazılır.
- GitHub deposuna ham görüntü, etiket veya model çıktısı yüklenmez.
- Test görüntüsü eğitim için kullanılmaz; eğitim/test ayrımı korunur.
- Görüntüdeki kişiler gerçek çalışanımız gibi tanıtılmaz ve otomatik ihlal kararı verilmiş gibi sunulmaz.

## Seçilen Pexels video adayları

Pexels lisans sayfası fotoğraf ve videoların ücretsiz kullanılabildiğini,
değiştirilebildiğini ve atfın zorunlu olmadığını belirtiyor. Aynı lisans,
tanınabilir kişilerin kötü veya saldırgan bir bağlamda gösterilmesini ve kişinin
ürünü desteklediği izlenimini vermeyi yasaklıyor.

Bu nedenle Pexels videoları yalnız **uygun ekipman bulunan pozitif senaryo** ve
video okuma/takip deneyi için kullanılacak. Bu kişilere “ihlal yapan çalışan”
etiketi verilmeyecek. Atıf zorunlu olmasa da proje kaydında üretici tutulacak.

1. **Construction Workers Walking at the Construction Site**
   - Üretici: Mikael Blomkvist
   - Sayfa: https://www.pexels.com/video/construction-workers-walking-at-the-construction-site-8965526/
   - İçerik: Baret ve reflektif yelekli iki çalışanın şantiyede yürüyüşü.
   - Planlanan kullanım: pozitif baret/yelek ve kişi takibi testi.
2. **Workers Walking in Construction Site**
   - Üretici: Everett Bumstead
   - Sayfa: https://www.pexels.com/video/workers-walking-in-construction-site-5434223/
   - İçerik: Kapalı inşaat alanında koruyucu ekipmanlı çalışanlar.
   - Planlanan kullanım: birden fazla kişi ve iç mekân video hattı testi.

Lisans sayfası: https://www.pexels.com/license/

Video indirilirken şu bilgiler `data/demo/SOURCES.md` adlı yerel kayda yazılacak:
sayfa bağlantısı, üretici, indirme tarihi, dosya adı, dosya SHA-256 değeri ve
indirme anındaki lisans bağlantısı. `data/demo/SOURCES.md` de kişisel çalışma
verisiyle birlikte Git dışında kalır; paylaşılabilir kaynak özeti bu belgede tutulur.

## Kendi eksik ekipman canlandırmamız

Negatif/eksik ekipman gösterimi için en güvenli kaynak, projeyi bilen bir kişinin
kontrollü biçimde çekilmiş kısa canlandırmasıdır. Bu kayıt gerçek iş güvenliği
ihlali olarak tanıtılmaz.

Kayıttan önce:

- Görüntüdeki kişi projenin amacı ve kaydın nerede gösterileceği konusunda bilgilendirilir.
- Kayıt ve bitirme projesi gösterimi için açık onayı alınır.
- Gerçek iş yeri, şirket adı, çalışan kartı, araç plakası veya özel bilgi görünmez.
- Tehlikeli davranış yapılmaz; yalnız güvenli alanda ekipman takma/çıkarma canlandırılır.
- Otomatik kişi tanıma denenmez ve kişiye gerçek ihlal geçmişi oluşturulmaz.

Kayıttan sonra:

- Dosya `data/demo/own/` altında tutulur ve Git'e eklenmez.
- Kişinin adı yerine `gonullu-01` gibi bir demo kodu kullanılır.
- Onay geri çekilirse görüntü demo kaynaklarından çıkarılır.
- Raporlarda sonuçlar “canlandırılmış demo” olarak belirtilir.

Kullanıcının kendisinin yer aldığı webcam kaydı için de aynı saklama ve sunum
kuralları uygulanır. İlk model testi için bu kayıt hemen gerekli değildir.

## Demo sırasında kullanılmayacak içerikler

- Kaynağı veya lisansı belli olmayan sosyal medya/YouTube görüntüleri.
- İzinsiz iş yeri güvenlik kamerası kaydı.
- Gerçek bir kişiyi küçük düşürecek, suçlayacak veya disiplin ihlali yapmış gibi gösterecek stok görüntü.
- Yüz tanıma amacıyla toplanmış fotoğraflar.
- Model başarısını olduğundan iyi göstermek için yalnız seçilmiş başarılı örnekler.

## Sonraki adım

Pexels videosunu indirmek B2 için zorunlu değil; önce GPU ve model kurulumu
doğrulanacak. Video hattına geçtiğimizde seçilen dosya indirilip kaynak kaydı
ve bütünlük değeri oluşturulacak. İlk model çıkarımı Construction-PPE test
görüntülerinden biriyle yapılabilir.

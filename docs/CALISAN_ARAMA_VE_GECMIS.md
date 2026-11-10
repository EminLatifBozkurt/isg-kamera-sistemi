# Çalışan arama ve otomatik olay geçmişi — D5

Bu aşama çalışan profil ekranının ihtiyaç duyacağı okuma sözleşmesini tamamlar.
Amaç aynı adlı kişileri karıştırmadan bulmak, yalnız otomatik kimlik eşleşmesiyle
bağlanmış olayları göstermek ve çalışan pasifleştirilse bile geçmişi korumaktır.

## Arama ve sayfalama

`GET /api/v1/employees` şu parametreleri kabul eder:

| Parametre | Davranış |
|---|---|
| `q` | Ad, çalışan numarası veya bölüm içinde büyük/küçük harfsiz arama |
| `include_inactive` | `true` ise pasif çalışanları da getirir |
| `limit` | 1–100 arasında sayfa büyüklüğü; varsayılan 50 |
| `offset` | Atlanacak kayıt sayısı; varsayılan 0 |

`%`, `_` ve ters bölü karakterleri SQL LIKE jokeri gibi çalıştırılmaz; metin
olarak kaçırılır. Sonuçlar ad ve ardından çalışan numarasıyla sıralanır. Aynı tam
ada sahip kişiler benzersiz çalışan numarasıyla ayırt edilir.

## Olay geçmişi

`GET /api/v1/employees/{employee_id}/events`, en yeni olaydan eskiye doğru şu
bilgileri döndürür:

- olay, kamera ve olay anındaki kural sürümü kimlikleri;
- kamera adı ve model sürümü;
- otomatik kimlik, teknik yaşam döngüsü ve İSG inceleme durumu;
- başlangıç, son görülme, bitiş ve kayıtlı video zamanı;
- ekipman kodu, uygunluk sonucu ve gözlem sayısını içeren bulgular.

Bu uç yalnız `safety_event.employee_id` ile otomatik bağlanmış olayları okur.
İSG görevlisinin geçmişi elle başka çalışana taşıyacağı bir API yoktur. Bilinmeyen
ve belirsiz kimlikli olaylar çalışan geçmişine eklenmez.

## Özet

`GET /api/v1/employees/{employee_id}/history-summary` şu sayıları ayrı döndürür:

- toplam olay;
- inceleme bekleyen olay;
- doğrulanmış olay;
- yanlış alarm;
- son olay zamanı.

Bekleyen kayıt, doğrulanmış ihlal gibi sayılmaz. Yanlış alarm da doğrulanmış olay
sayısını artırmaz. Bu ayrım çalışan profilinde yanıltıcı toplam gösterilmesini
önler.

## Pasifleştirme ve geçmiş koruması

Çalışan pasifleştirildiğinde satır silinmez. Varsayılan listede görünmez ancak
`include_inactive=true` ile bulunabilir. Ayrıntı, geçmiş ve özet uçları pasif kişi
için de çalışır. Yabancı anahtar nedeniyle eski olayların çalışan bağlantısı
korunur.

## Gerçek kabul deneyi

`scripts/verify_employee_history.py` gerçek PostgreSQL ve ASGI uygulamasında:

1. aynı ada sahip iki çalışanı farklı numaralarla oluşturdu;
2. ad aramasında iki ayrı numarayı da buldu;
3. ilk çalışana otomatik tanınmış iki olay ve baret ihlali bulgusu bağladı;
4. geçmişte iki olayı, özette bir bekleyen ve bir doğrulanmış kaydı gördü;
5. çalışanı pasifleştirdi;
6. etkin listeden çıktığını, tüm kayıt listesinde ve olay geçmişinde kaldığını
   doğruladı;
7. bütün geçici kayıtları temizleyip PostgreSQL'i kapattı.

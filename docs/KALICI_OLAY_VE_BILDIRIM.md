# Kalıcı olay kaydı ve yeniden bağlanabilir bildirim — E4

Bu aşamada E1–E3 tarafından üretilen geçici sonuçlar PostgreSQL kayıtlarına
dönüştürüldü. Temel kural şudur: **önce veritabanına commit, sonra bildirim**.
WebSocket bir kolaylık katmanıdır; olayın asıl kaynağı değildir.

## Kalıcı yazma akışı

`event_store.py`, E2 `EventTransition` komutlarını şu şekilde uygular:

- `started`: tek `safety_event`, o anda bilinen ekipman bulguları, bir fotoğraf ve
  bir klip için `preparing` medya satırları oluşturur;
- `updated`: aynı olayın son görülme zamanını ve ekipman bulgularını günceller;
  yeni bir ekipman eksikliği ortaya çıktıysa değişiklik kaydı üretir;
- `ended`: teknik durumu `ended` yapar, bitiş zamanını ve açık bitiş nedenini saklar;
- E3 sonucu `ready` olduğunda göreli yol, MIME türü, boyut ve SHA-256 değerlerini;
  `failed` olduğunda hata durumunu iki medya satırına yazar.

Olay UUID'si tekrar gelirse aynı başlangıç çoğaltılmaz. Ancak aynı UUID farklı
kamera, oturum, takip, kural, kişi veya model sürümüyle gelirse veri karışmasını
önlemek için reddedilir. Her olayda yalnız bir `snapshot` ve bir `clip` satırına
veritabanı benzersizlik kuralı kondu.

## Sıralı değişiklik kaydı

Yeni `event_change` tablosunun artan sayısal kimliği bildirim imlecidir. Değişiklik
türleri şunlardır:

- `event_started`
- `event_updated`
- `event_ended`
- `media_ready`
- `media_failed`

Bu tablo WebSocket bağlantısından bağımsızdır. Panel kapalıyken veya ağ kopukken
satırlar PostgreSQL'de kalır. Her satır olay UUID'si, küçük JSON yükü ve UTC zamanı
taşır. Büyük görüntü/video veritabanına gömülmez.

## Panelin yeniden bağlanması

- `GET /api/v1/events?offset=0&limit=50`: veritabanındaki gerçek olayların sayfalı
  listesini, çalışan/kamera bilgisini, ekipmanları ve medya durumlarını verir.
- `GET /api/v1/events/changes?after_id=N`: panelin en son gördüğü değişiklikten
  sonrakileri artan sırada verir.
- `WS /api/v1/events/live?after_id=N`: aynı imleçten başlayıp yeni değişiklikleri
  yaklaşık bir saniyelik PostgreSQL sorgusuyla iletir.

WebSocket koparsa panel son `cursor` değerini koruyup tekrar bağlanır. Arada kaçan
satırlar önce veritabanından gelir; yalnız bellekte tutulan bildirim yoktur. İlk
sürümde Redis/Celery gerekmez. Kamera ve panel sayısı büyürse sorgu yükü ölçülüp
daha sonra PostgreSQL LISTEN/NOTIFY veya ayrı mesaj altyapısı değerlendirilebilir.

## Yetkilendirme

Olay listesi, değişiklik listesi ve WebSocket yalnız `admin` veya `isg` rolündeki
geçerli sunucu oturumlarını kabul eder. WebSocket tarayıcının HttpOnly oturum
cookie'sini doğrular; ham oturum doğrulayıcısı veritabanında bulunmaz. Geçerli canlı
bağlantı oturumun son görülme ve boşta kalma süresini güvenli sınırlar içinde uzatır.

## Gerçek PostgreSQL doğrulaması

`scripts/verify_event_store.py` şu akışı gerçek yerel PostgreSQL üzerinde yaptı:

1. Kamera, oturum ve kural sürümü oluşturdu.
2. Panel açılmadan olayı başlattı, güncelledi, bitirdi ve medya sonucunu yazdı.
3. Aynı başlangıç komutunu tekrar oynatıp olay/medya/değişiklik çoğalmadığını gördü.
4. Sıralı değişiklikleri `started → updated → ended → media_ready` olarak okudu.
5. Paneli daha sonra açıp olayın tam listede bulunduğunu doğruladı.
6. WebSocket'i sondan bir önceki imleçle bağlayıp yalnız kaçırılan `media_ready`
   kaydını aldı.
7. Geçici kamera, olay ve kullanıcı kayıtlarını temizleyip PostgreSQL'i kapattı.

Migration yalnız güvenli ileri yönde uygulandı. Geliştirme veritabanındaki gerçek
değişiklik satırlarını silebileceği için otomatik downgrade deneyi yapılmadı.

## Sonraki görev

E5, İSG görevlisinin açıklamasını ve karar düzeltmelerini eklemeli; eski kararları
güncellemek yerine eklemeli `event_review_revision` geçmişi oluşturmalıdır. Yanlış
alarm çalışanın doğrulanmış ihlal sayısını artırmamalıdır.

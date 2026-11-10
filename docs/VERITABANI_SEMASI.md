# Veritabanı şeması — D2 uygulama sözleşmesi

Bu belge, SQLAlchemy modelleri ve ilk Alembic şema değişikliği yazılmadan önce
kalıcı kayıtların sınırlarını belirler. Amaç yalnız tablo adlarını listelemek değil;
geçmiş olayların kamera, kural veya çalışan kaydı değiştiğinde bozulmasını
engellemektir.

## Temel kararlar

- PostgreSQL kullanılacak. Tarihler `timestamp with time zone` olarak UTC
  saklanacak; panelde `Europe/Istanbul` saatine çevrilecek.
- Ana kayıt kimlikleri UUID olacak. Kullanıcıya gösterilen çalışan numarası gibi
  iş alanları UUID yerine geçmeyecek.
- Kamera, çalışan ve ekipman gibi geçmişte bir olaya bağlanan kayıtlar fiziksel
  olarak silinmeyecek; `is_active` ile pasifleştirilecek.
- Kural sürümleri değiştirilmeyecek. Yeni ayar kaydedildiğinde yeni sürüm
  oluşturulacak ve eski olay kendi sürümüne bağlı kalacak.
- Fotoğraf ve video veritabanına gömülmeyecek. Veritabanında yetkili sunucu
  üzerinden erişilecek göreli dosya yolu, boyut, özet ve hazırlık durumu tutulacak.
- Yüz tanıma sonucu güvenilir değilse olayın `employee_id` alanı boş kalacak.
  İSG görevlisi olayı başka bir çalışana elle atamayacak.
- İnceleme değişiklikleri mevcut satırın üstüne yazılmayacak; eklemeli geçmiş
  olarak tutulacak. Böylece kim, ne zaman, hangi kararı verdi görülebilecek.
- Ekipman kataloğu uygulamayla gelen sabit kodlardan oluşacak. Arayüzden yeni
  ekipman türü ekleme ve silme yapılmayacak.

## Ana tablolar

### `equipment_definition`

Sabit ekipman kataloğunu tutar.

| Alan | Amaç |
|---|---|
| `code` | `helmet`, `vest`, `gloves`, `goggles`, `boots` gibi sabit anahtar |
| `display_name` | Panelde gösterilecek Türkçe ad |
| `model_class` | Model çıktısındaki sınıf adı; desteklenmiyorsa boş olabilir |
| `is_model_supported` | Modelin bu ekipmanı gerçekten değerlendirebildiğini belirtir |

`code` birincil anahtardır. Kullanıcı bu tabloya serbest kayıt ekleyemez.

### `camera`

Mantıksal kamera kaydıdır; webcam, kayıtlı demo videosu veya ileride desteklenen
ağ kamerası aynı tabloda bulunur.

| Alan | Amaç |
|---|---|
| `id` | UUID birincil anahtar |
| `name` | Kullanıcının gördüğü benzersiz kamera adı |
| `source_type` | `webcam`, `recorded_video` veya `rtsp` |
| `source_config` | Parola içermeyen kaynak ayarları |
| `is_active` | Yeni analiz oturumu açılıp açılamayacağı |
| `created_at`, `updated_at` | Kayıt zamanları |

RTSP kullanıcı adı/parolası düz metin JSON içine yazılmayacak. Gizli bilgi
yönetimi D4'te ayrıca uygulanacak. Kamera silme yerine pasifleştirme yapılacak.

### `camera_session`

Bir kaynağın tek çalışma/yeniden oynatma dönemidir. Takip numaraları yalnız bu
oturum içinde anlamlıdır.

| Alan | Amaç |
|---|---|
| `id` | UUID oturum kimliği |
| `camera_id` | Bağlı kamera |
| `source_type` | O anda kullanılan kaynak türünün tarihsel kopyası |
| `started_at`, `ended_at` | Başlangıç ve isteğe bağlı bitiş zamanı |
| `end_reason` | Kullanıcı durdurdu, kaynak bitti, bağlantı koptu gibi neden |
| `source_started_at` | Kayıtlı videoda kaynak zamanının başlangıcı |

Bir oturum bittiğinde tekrar açılmaz. Yeniden bağlanma veya videoyu baştan
oynatma yeni oturum oluşturur.

### `employee`

Çalışan profilini tutar.

| Alan | Amaç |
|---|---|
| `id` | UUID birincil anahtar |
| `employee_number` | Aynı adlı kişileri ayıran benzersiz çalışan numarası |
| `full_name` | Ad ve soyad |
| `department` | Bölüm bilgisi |
| `is_active` | Yeni yüz eşleşmesine katılıp katılmayacağı |
| `created_at`, `updated_at` | Kayıt zamanları |

Pasif çalışan eski olay geçmişinde görünmeye devam eder. Yüz örnekleri ve yüz
özetleri K2'de ayrı tabloda ele alınacak; ham yüz fotoğrafı bu tabloya konmayacak.

### `rule_version`

Bir kameranın belirli anda geçerli olan değiştirilemez kural sürümüdür.

| Alan | Amaç |
|---|---|
| `id` | UUID sürüm kimliği |
| `camera_id` | Kuralların ait olduğu kamera |
| `version_number` | Kamera içinde artan sürüm numarası |
| `valid_from`, `valid_until` | Geçerlilik aralığı |
| `definition` | Kamera temeli, normalize bölgeler ve ekipman kodlarının JSONB anlık görüntüsü |
| `definition_hash` | Aynı tanımın gereksiz yeni sürüm oluşturmasını engelleyen özet |
| `created_by`, `created_at` | Değişikliği yapan kullanıcı ve zaman |

`(camera_id, version_number)` benzersizdir. Aynı kamerada geçerlilik aralıkları
çakışmayacak şekilde uygulama ve veritabanı kısıtı kurulacak. Çokgen noktaları
0–1 aralığında normalize koordinatlar olarak saklanacak. Eski sürüm güncellenmez.

### `safety_event`

Analizin kalıcı hale getirdiği tek hedef kişiye ait olaydır.

| Alan | Amaç |
|---|---|
| `id` | UUID olay kimliği |
| `camera_id`, `camera_session_id` | Kamera ve olayın oluştuğu tek oturum |
| `rule_version_id` | Olay anındaki değiştirilemez kural |
| `track_id` | Yalnız oturum içinde anlamlı takip numarası |
| `employee_id` | Güvenilir yüz eşleşmesi varsa çalışan; aksi halde boş |
| `identity_status` | `recognized`, `unknown` veya `ambiguous` |
| `technical_status` | `active` veya `ended` |
| `review_status` | `pending`, `confirmed` veya `false_alarm` |
| `started_at`, `last_seen_at`, `ended_at` | Olay zamanları |
| `source_time_ms` | Kayıtlı demo videosundaki zaman; canlı kaynakta boş olabilir |
| `end_reason` | Düzelme, gözlem kaybı, oturum sonu gibi bitiş nedeni |
| `model_version` | Olayı üreten modelin sürümü |
| `created_at`, `updated_at` | Kayıt zamanları |

`(camera_session_id, track_id, rule_version_id)` alanları olay birleştirme
işleminde kullanılır ancak tek başına benzersiz yapılmaz; aynı kişi farklı zaman
aralıklarında ayrı olay yaşayabilir. Çalışan bağlantısı yalnız otomatik kimlik
sonucuyla oluşur. Yanlış eşleşme kaldırıldığında alan boşaltılır ve değişiklik
geçmişe yazılır.

### `event_finding`

Bir olayda değerlendirilen ekipmanların sonuçlarını ayrı ayrı tutar.

| Alan | Amaç |
|---|---|
| `id` | UUID bulgu kimliği |
| `event_id` | Bağlı olay |
| `equipment_code` | Sabit ekipman kataloğu kodu |
| `assessment` | `compliant`, `violation` veya `not_evaluable` |
| `first_observed_at`, `last_observed_at` | Gözlem aralığı |
| `observation_count` | Kararı destekleyen sınırlı gözlem sayısı |
| `evidence_summary` | Güven değerleri ve görünürlük gibi küçük JSONB özet |

Bir olayda aynı ekipman kodu yalnız bir kez bulunur. Tüm model kareleri saklanmaz.

### `media_record`

Olay fotoğrafı ve kısa klibin dosya yaşam döngüsünü tutar.

| Alan | Amaç |
|---|---|
| `id` | UUID medya kimliği |
| `event_id` | Bağlı olay |
| `media_type` | `snapshot` veya `clip` |
| `status` | `preparing`, `ready`, `failed` veya `deleted` |
| `relative_path` | Medya köküne göre yol; tarayıcıya doğrudan açık yol değil |
| `mime_type`, `size_bytes`, `sha256` | Dosya doğrulama bilgileri |
| `started_at`, `ready_at`, `deleted_at` | Yaşam döngüsü zamanları |
| `error_message` | Hazırlama hatasının kişisel bilgi içermeyen özeti |

`ready` durumundaki kaydın yolu, boyutu ve özeti bulunmalı; `deleted` durumunda
olay kaydı korunurken dosyanın artık olmadığı açıkça anlaşılmalıdır.

### `event_review_revision`

İSG incelemesinin eklemeli ve değiştirilemez geçmişidir.

| Alan | Amaç |
|---|---|
| `id` | UUID değişiklik kimliği |
| `event_id` | İncelenen olay |
| `revision_number` | Olay içinde artan sıra |
| `previous_status`, `new_status` | Karar değişikliği |
| `note` | Görevlinin isteğe bağlı açıklaması |
| `reviewed_by`, `created_at` | İşlemi yapan kullanıcı ve zaman |

`(event_id, revision_number)` benzersizdir. Eski inceleme satırları güncellenmez
ve silinmez. `safety_event.review_status` hızlı sorgu için son durumu taşır;
geçmişin asıl kaynağı bu tablodur.

## D3 ve sonraki görevlerde eklenecek tablolar

İlk D2 değişikliği çekirdek olay akışını kuracak. Aşağıdaki kayıtlar görevleriyle
birlikte eklenecek ve çekirdek tablolara sonradan yabancı anahtar bağlayacak:

- D3: `app_user`, `user_session` ve güvenlik/denetim kayıtları.
- D4: kamera kaynağı gizli bilgileri ve yönetim değişiklikleri.
- K2: çalışan yüz özeti ve izinli yüz kayıtlarının yaşam döngüsü.
- E4: sıralı `notification_change` kayıtları.
- E5: inceleme notları ve kimlik bağlantısı kaldırma denetim ayrıntıları.
- F4: kullanıcı bazlı olay okuma kayıtları.

D2 sırasında `created_by` ve `reviewed_by` alanları kullanıcı tablosu henüz yoksa
geçici olarak boş bırakılabilir; D3 değişikliği gerçek yabancı anahtarı kurar.

## Silme ve ilişki kuralları

- Kamera → oturum/kural/olay: geçmiş kayıt varsa fiziksel silme reddedilir.
- Çalışan → olay: çalışan pasifleştirilir; geçmiş olay bağlantısı korunur.
- Kural sürümü → olay: silme ve güncelleme reddedilir.
- Olay → bulgu/medya/inceleme: normal uygulamada olay silinmez. Test verisi
  temizliği için yalnız yönetilen bakım işlemi kullanılabilir.
- Medya dosyası → olay: saklama süresi dolduğunda yalnız dosya ve medya durumu
  değişir; olay ve inceleme geçmişi kalır.

## Önemli indeksler ve kısıtlar

- `camera(name)` ve `employee(employee_number)` benzersiz.
- `camera_session(camera_id, started_at desc)`.
- `rule_version(camera_id, version_number)` benzersiz ve
  `rule_version(camera_id, valid_from desc)`.
- `safety_event(camera_id, started_at desc)`.
- `safety_event(review_status, started_at desc)`; bekleyen olay listesini hızlandırır.
- `safety_event(employee_id, started_at desc)`; çalışan geçmişini hızlandırır.
- `safety_event(camera_session_id, track_id, technical_status)`; olay birleştirmeye
  yardımcı olur.
- `event_finding(event_id, equipment_code)` benzersiz.
- `media_record(event_id, media_type)` ve `media_record(status)`.
- `event_review_revision(event_id, revision_number)` benzersiz.
- Zaman sırası kısıtları: bitiş başlangıçtan önce olamaz; son görülme olay
  başlangıcından önce olamaz; medya boyutu negatif olamaz.

## İlk Alembic değişikliğinin sırası

1. PostgreSQL eklentisi gerektirmeyen UUID alanlarını ve ortak adlandırma
   kurallarını hazırla.
2. Ekipman kataloğu, kamera ve çalışan tablolarını oluştur.
3. Kamera oturumu ve değiştirilemez kural sürümünü oluştur.
4. Olay, ekipman bulgusu, medya ve inceleme geçmişini oluştur.
5. Sabit ekipman kodlarını veri değişikliği olarak ekle.
6. Kısıtları ve listeleme indekslerini kur.
7. Boş PostgreSQL veritabanında yükseltme, geri alma ve yeniden yükseltme deneyi
   yap; sonuçları belgeleyip ancak bundan sonra D2'yi tamamlandı say.

## D2 tamamlanma kontrolü

- SQLAlchemy 2 modelleri tipli ve ortak metadata ile yazılmış olmalı.
- Alembic ilk değişikliği boş veritabanına hatasız uygulanmalı.
- Oluşan tablo, yabancı anahtar, benzersizlik ve kontrol kısıtları test edilmeli.
- Geri alma işlemi şemayı temiz biçimde kaldırmalı; tekrar yükseltme geçmeli.
- Eski olayın kural sürümünü değiştiren veya geçmiş kaydı yanlışlıkla silen
  işlemler reddedilmeli.
- Parola, RTSP gizli bilgisi ve yüz fotoğrafı migration veya Git geçmişine
  girmemeli.

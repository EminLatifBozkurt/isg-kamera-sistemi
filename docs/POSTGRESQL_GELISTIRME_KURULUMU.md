# PostgreSQL geliştirme kurulumu — D1

## Doğrulanan kurulum

10 Kasım 2026 tarihinde Windows üzerinde aşağıdaki ortam kuruldu ve gerçek
bağlantıyla doğrulandı:

- PostgreSQL 18.6, UTF-8 veri kodlaması.
- ICU `tr-TR` metin sıralaması ve `Europe/Istanbul` sunucu saat dilimi.
- `isg_kamera` veritabanı ve yalnız uygulamanın kullandığı `isg_app` rolü.
- SQLAlchemy 2.1.8, Alembic 1.20.1 ve Psycopg 3.3.8.
- Python bağımlılık kilidi: `backend/requirements-database.lock.txt`.

Uygulama hesabı PostgreSQL superuser değildir. Gerçek parolalar depoya, README'ye
veya `.env.example` içine yazılmadı.

## Windows'taki çalışma biçimi

EDB kurucusu bilgisayarın otomatik ürettiği `Turkish_Türkiye.1254` adındaki
ASCII dışı karakteri yanlış kodladığı için ilk küme oluşturma adımı başarısız
oldu. Program dosyaları ve paket özeti sağlamdı. Boş veri alanı PostgreSQL'in
kendi `initdb` aracıyla şu mantıkta yeniden oluşturuldu:

- genel libc ayarları: `C`;
- gerçek metin karşılaştırma sağlayıcısı: ICU;
- ICU dili: `tr-TR`;
- veri kodlaması: UTF-8;
- istemci kimlik doğrulaması: SCRAM-SHA-256;
- veri sayfası sağlama toplamları: etkin.

Windows servis kaydı yönetici yetkisi gerektirdiği için geliştirme ortamında
PostgreSQL kullanıcı süreci olarak çalışır. Bu bir hata değildir:

1. `PROJEYI_BASLAT.cmd`, PostgreSQL kapalıysa `pg_ctl` ile başlatır.
2. Windows kullanıcı ortamındaki parolayı yalnız başlattığı FastAPI sürecine verir.
3. `isg_app` ile gerçek `SELECT 1` çalışmadan paneli hazır saymaz.
4. `PROJEYI_DURDUR.cmd`, FastAPI ve React ile birlikte PostgreSQL'i de kontrollü
   `fast` kapanışla durdurur.

Kurulum yolu bu bilgisayarda `C:\Program Files\PostgreSQL\18` olarak sabittir.
Başka bilgisayara kurulum yapılırsa başlatma betiklerindeki yol da güncellenmelidir.

## Gizli ayarlar

Yerel kurulumda parola Windows kullanıcı ortamındaki
`ISG_DATABASE_PASSWORD` değişkenindedir. Başlatıcı bu değeri ekrana yazmaz.
PostgreSQL yönetici parolası uygulamaya verilmez ve ayrı
`ISG_POSTGRES_ADMIN_PASSWORD` kullanıcı ortamında tutulur.

Başka bir kurulum biçiminde Git'in dışladığı `.env` dosyası da kullanılabilir:

```dotenv
ISG_DATABASE_HOST=127.0.0.1
ISG_DATABASE_PORT=5432
ISG_DATABASE_NAME=isg_kamera
ISG_DATABASE_USER=isg_app
ISG_DATABASE_PASSWORD=GERCEK_YEREL_PAROLA
ISG_DATABASE_POOL_SIZE=5
ISG_DATABASE_CONNECT_TIMEOUT_SECONDS=5
```

Uygulama parolayı Pydantic `SecretStr` olarak tutar. Loglanabilen bağlantı hedefi
yalnız host, port, veritabanı ve kullanıcı adını içerir. SQLAlchemy URL gösterimi
de parolayı gizler.

## Yapılan doğrulamalar

- `psql` ile `isg_kamera|isg_app|18.6|UTF8|Europe/Istanbul` sonucu alındı.
- Projenin `create_database_engine` ve `check_database_connection` koduyla gerçek
  `SELECT 1` sorgusu geçti.
- Bilerek yanlış parola reddedildi.
- PostgreSQL kontrollü kapatıldığında uygulama bağlantısı başarısız oldu; sunucu
  yeniden başlatıldığında durum tekrar `ok` oldu.
- Kapalı sunucuda yaklaşık 90 saniyelik varsayılan sürücü beklemesi ölçüldü ve
  ayarlanabilir `ISG_DATABASE_CONNECT_TIMEOUT_SECONDS=5` sınırı eklendi.
- Health API gerçek bağlantıda `database: ok`, bağlantı hatasında `unavailable`,
  parola ayarlanmamışsa `not_configured` döndürür.
- Tek tık başlatma testinde PostgreSQL, FastAPI ve React birlikte açıldı; health
  yanıtı `database: ok`, panel HTTP 200 döndürdü.
- Yanlış parola ve bağlantı hatası metinleri health yanıtına veya panele
  taşınmadı.

## Paketleri başka bilgisayarda kurma

PostgreSQL 18 kurulduktan ve yerel rol/veritabanı hazırlandıktan sonra Python
paketleri şu kilitli dosyayla kurulur:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-database.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ./backend
```

D1 tamamlandı. D2'de SQLAlchemy modelleri ve ilk Alembic şema değişikliği gerçek
`isg_kamera` veritabanında yükseltme–geri alma–yeniden yükseltme ile sınanacak.

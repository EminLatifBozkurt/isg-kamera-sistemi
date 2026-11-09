# PostgreSQL Geliştirme Kurulumu — D1

## Mevcut durum

Bilgisayarda PostgreSQL, `psql`, Docker veya Podman bulunmuyor. Bağlantı ayarları
ve kontrol kodu hazırlandı; gerçek sunucu bağlantısı henüz kurulmadığı için D1
tamamlandı olarak işaretlenmedi.

## Güvenli ayarlar

Gerçek parola depoya yazılmaz. `.env.example` kopyalanarak Git'in dışladığı
`.env` dosyası oluşturulacak:

```dotenv
ISG_DATABASE_HOST=127.0.0.1
ISG_DATABASE_PORT=5432
ISG_DATABASE_NAME=isg_kamera
ISG_DATABASE_USER=isg_app
ISG_DATABASE_PASSWORD=GERCEK_YEREL_PAROLA
ISG_DATABASE_POOL_SIZE=5
```

Uygulama parolayı Pydantic `SecretStr` olarak tutar. Loglanabilen bağlantı hedefi
yalnız host, port, veritabanı ve kullanıcı adını içerir.

## Onaydan sonra yapılacaklar

1. Resmî PostgreSQL Windows sayfasının yönlendirdiği EDB kurucusuyla yalnız
   gerekli sunucu/komut satırı bileşenlerini kur.
2. `isg_app` kullanıcısı ile `isg_kamera` veritabanını oluştur; uygulamaya
   superuser parolası verme.
3. SQLAlchemy 2, psycopg 3 ve Alembic'i sabit sürümlerle sanal ortama kur.
4. Gerçek `SELECT 1` bağlantı kontrolünü çalıştır.
5. Yanlış parola ve kapalı sunucu durumlarının sağlıklı görünmediğini doğrula.

Kurucu yaklaşık 300–400 MB indirme, bileşenler ve ilk veri alanı yaklaşık 1–2 GB
disk gerektirebilir. Python paketleri ayrıca birkaç on MB kullanabilir. Kesin
değer seçilen PostgreSQL sürümü ve pgAdmin bileşenine göre değişir; indirme
kullanıcı onayı olmadan başlatılmaz.

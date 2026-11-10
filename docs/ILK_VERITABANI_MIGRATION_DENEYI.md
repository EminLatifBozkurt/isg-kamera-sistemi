# İlk veritabanı migration deneyi — D2

## Amaç

Çekirdek kalıcı kayıt yapısının yalnız Python sınıfları olarak değil, gerçek
PostgreSQL üzerinde kurulup geri alınabilen ve hatalı kayıtları reddeden bir şema
olduğunu doğrulamak.

## Ortam

- Tarih: 10 Kasım 2026
- PostgreSQL: 18.6
- Veritabanı: `isg_kamera`
- Uygulama rolü: `isg_app` (superuser değil)
- SQLAlchemy: 2.1.8
- Alembic: 1.20.1
- Psycopg: 3.3.8
- Migration: `20261110_0001`

Parola komutlara, rapora veya Git dosyalarına yazılmadı; Windows kullanıcı
ortamından alındı.

## Oluşturulan tablolar

1. `equipment_definition`
2. `camera`
3. `employee`
4. `camera_session`
5. `rule_version`
6. `safety_event`
7. `event_finding`
8. `media_record`
9. `event_review_revision`

Alembic ayrıca kendi `alembic_version` tablosunu yönetir.

## Katalog verisi

Migration, arayüzden serbestçe değiştirilmeyecek beş ekipman kodunu ekledi:

| Kod | Görünen ad | Model sınıfı |
|---|---|---|
| `helmet` | Baret | `helmet` |
| `vest` | Reflektif yelek | `vest` |
| `gloves` | Eldiven | `gloves` |
| `goggles` | Koruyucu gözlük | `goggles` |
| `boots` | İş botu | `boots` |

## Uygulanan deney

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini check
.\.venv\Scripts\python.exe scripts/verify_database_schema.py
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini downgrade base
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe scripts/verify_database_schema.py
```

## Doğrulanan davranışlar

- Dokuz uygulama tablosu ve Alembic sürüm tablosu eksiksiz oluştu.
- Beş sabit ekipman kodu doğru geldi.
- Geçerli kamera, çalışan, oturum, kural, olay, bulgu, hazırlanan medya ve inceleme
  kayıtları aynı transaction içinde yazılabildi.
- `identity_status=recognized` olup `employee_id` taşımayan olay reddedildi.
- Aynı kameraya aynı anda ikinci güncel kural sürümü eklemek reddedildi.
- Dosya yolu, MIME türü, boyut, SHA-256 ve hazır olma zamanı bulunmayan
  `status=ready` medya kaydı reddedildi.
- Geçmiş oturumu/kuralı/olayı bulunan kamera fiziksel olarak silinemedi.
- Deneme kayıtları transaction sonunda geri alındı; veritabanında yalnız sabit
  katalog kaldı.
- Geri alma sonrası yalnız `alembic_version` tablosu kaldı.
- Yeniden yükseltme aynı şemayı ve katalog verisini eksiksiz oluşturdu.
- Son `alembic check` sonucu: `No new upgrade operations detected.`

## Sonuç

D2 tamamlandı. Şema geçmiş kayıtları koruyor, kritik tutarsızlıkları yalnız
uygulama koduna güvenmeden PostgreSQL seviyesinde reddediyor ve temiz biçimde
geri alınıp yeniden uygulanabiliyor.

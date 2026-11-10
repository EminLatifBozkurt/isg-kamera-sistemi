# Kimlik doğrulama ve yetki — D3

## Seçilen yaklaşım

Panel şirket içinde aynı kaynaktan çalışacağı için JWT yerine PostgreSQL'de
tutulan, iptal edilebilir sunucu oturumu kullanılır. Tarayıcıda oturum kimliği
`localStorage` veya `sessionStorage` içine yazılmaz.

- Parola: `pwdlib` ile Argon2id.
- Oturum: UUID kimliği + 256 bit rastgele doğrulayıcı.
- Sunucu kaydı: yalnız doğrulayıcının SHA-256 özeti.
- Cookie: HttpOnly, SameSite=Strict, Path=/.
- CSRF: ayrı 256 bit cookie değeri ile `X-CSRF-Token` başlığının eşleşmesi ve
  veritabanındaki özetin sabit zamanlı doğrulanması.
- Roller: `admin` ve `isg`.
- Süreler: 30 dakika hareketsizlik, 8 saat mutlak süre.
- Giriş koruması: varsayılan 5 yanlış denemeden sonra 15 dakika geçici kilit.

Bu kararlar [FastAPI parola özeti rehberi](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
ve [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
önerilerine dayanır.

## Neden JWT değil?

Bu uygulama tek şirket ağı ve tek PostgreSQL sunucusu hedefliyor. Sunucu oturumu:

- çıkışta veya hesap pasifleştirmede anında iptal edilebilir;
- rol değişikliğini bir sonraki istekte uygular;
- uzun ömürlü imzalı token yenileme/iptal listesi gerektirmez;
- panel kapalı olsa da sunucudaki denetimi korur.

## Veritabanında ne tutulur?

`app_user` tablosunda kullanıcı adı, görünen ad, Argon2id parola özeti, rol,
aktiflik, yanlış giriş sayısı ve kilit zamanı bulunur. Düz parola yoktur.

`user_session` tablosunda oturum UUID'si, kullanıcı, SHA-256 doğrulayıcı özeti,
CSRF özeti, oluşturulma/son görülme/bitiş ve iptal zamanları bulunur. Tarayıcıdaki
ham doğrulayıcı ve ham CSRF belirteci saklanmaz.

SHA-256 parola için kullanılmaz. Yalnız 256 bit rastgele oturum belirteçlerinde
hızlı tek yönlü doğrulayıcı olarak kullanılır; parola Argon2id ile korunur.

## Cookie adları ve HTTPS

Yerel `http://127.0.0.1` geliştirmede cookie adları `id` ve `csrf`, `Secure=false`
olarak kullanılır. H5 yerel ağ HTTPS kurulumunda
`ISG_SESSION_COOKIE_SECURE=true` yapılır; adlar otomatik `__Host-id` ve
`__Host-csrf` olur. `__Host-` cookie için Domain verilmez ve Path `/` kalır.

## API yolları

| Yöntem ve yol | Yetki | CSRF |
|---|---|---|
| `POST /api/v1/auth/login` | Açık; Origin kontrolü var | Oturum öncesi değil |
| `GET /api/v1/auth/me` | Geçerli oturum | Güvenli GET, gerekmez |
| `POST /api/v1/auth/logout` | Geçerli oturum | Zorunlu |
| `GET /api/v1/users` | Admin | Güvenli GET, gerekmez |
| `POST /api/v1/users` | Admin | Zorunlu |
| `PATCH /api/v1/users/{id}/active` | Admin | Zorunlu |
| `GET /api/v1/media/{id}` | Admin veya İSG | Güvenli GET, gerekmez |

Medya yolu şimdilik yalnız yetkili meta bilgisi döndürür. E3/F4 aşamasındaki
gerçek fotoğraf/klip sunumu da aynı oturum bağımlılığından geçecek; herkese açık
statik klasör kullanılmayacak.

## İlk yönetici

Varsayılan hesap veya depoda parola yoktur. PostgreSQL çalışırken:

```powershell
.\.venv\Scripts\python.exe scripts/create_initial_admin.py `
  --username emin `
  --display-name "Emin Bozkurt"
```

Betik parolayı iki kez görünmez biçimde ister. İlk kullanıcı zaten varsa yeni
hesap oluşturmaz; sonraki hesaplar yönetici API'sinden eklenir.

## Doğrulama

```powershell
.\.venv\Scripts\python.exe scripts/verify_auth_flow.py
```

Betik geçici admin/İSG hesaplarıyla 11 güvenlik senaryosunu çalıştırır ve tüm
deneme hesaplarını/oturumlarını sonunda siler. Gerçek kullanıcı veya parola
oluşturmaz.

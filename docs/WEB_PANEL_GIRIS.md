# Web paneli giriş ve oturum akışı — F1

F1 ile mevcut React/TypeScript paneli gerçek FastAPI oturum sistemine bağlandı.
Kamera, olay ve çalışan sayfaları artık oturum açmadan görüntülenemez.

## Açılış akışı

1. `AuthProvider`, uygulama açıldığında `GET /api/v1/auth/me` isteği gönderir.
2. Geçerli HttpOnly oturum cookie'si varsa kullanıcı ve rol bilgisi belleğe alınır.
3. Sunucu 401 döndürürse kullanıcı `/giris` sayfasına yönlendirilir.
4. Sunucuya erişilemiyorsa oturum yokmuş gibi davranmak yerine bağlantı hatası ve
   `Yeniden dene` düğmesi gösterilir.
5. Kontrol sürerken korumalı sayfalar kısa bir yükleme görünümü gösterir; panel
   içeriği yetkilendirme sonucu gelmeden çizilmez.

## Giriş ekranı

`LoginPage.tsx`, kullanıcı adı ve parolayı `POST /api/v1/auth/login` ucuna yollar.
Başarılı cevapta sunucunun döndürdüğü kullanıcı bilgisi kullanılır ve kullanıcı
başlangıçta gitmek istediği korumalı sayfaya döner. Hatalı kullanıcı adı/parolada
sunucunun hesap varlığını sızdırmayan ortak hata davranışı korunur.

Parola React durumunda yalnız form açıkken bulunur; localStorage veya sessionStorage'a
yazılmaz. Ham oturum doğrulayıcısı JavaScript tarafından okunamaz çünkü sunucu onu
HttpOnly cookie içinde tutar.

## Korumalı yönlendirme

`RequireAuth`, aşağıdaki yolları yalnız doğrulanmış oturuma açar:

- `/` genel bakış;
- `/kameralar`;
- `/olaylar`;
- `/calisanlar`.

`/giris` açık yoldur. Zaten giriş yapmış kullanıcı bu sayfaya giderse panele geri
yönlendirilir. Bilinmeyen panel yollarındaki 404 ekranı da oturum koruması içindedir.

## Kullanıcı ve güvenli çıkış

Üst çubuk kullanıcı görünen adını ve `Sistem yöneticisi` veya `İSG görevlisi`
rolünü gösterir. Çıkış düğmesi `POST /api/v1/auth/logout` isteğine tarayıcıdaki
CSRF cookie değerini başlık olarak ekler. Yerel HTTP için `csrf`, ilerideki HTTPS
kurulumu için `__Host-csrf` adı desteklenir. Başarılı çıkıştan sonra panel durumu
temizlenir ve giriş ekranına dönülür.

## Doğrulama

- ESLint hatasız tamamlandı.
- TypeScript katı tip kontrolü tamamlandı.
- Vite üretim derlemesi oluşturuldu.
- Gerçek PostgreSQL + FastAPI deneyinde yetkisiz erişim, farklı kaynaklı giriş,
  yanlış parola, güvenli cookie özellikleri, `/auth/me`, CSRF reddi, admin/İSG rol
  sınırı, ham belirteçlerin saklanmaması, güvenli çıkış ve geçici hesap kilidi olmak
  üzere 11 kontrol geçti.

Vite üretim derlemesi, JavaScript paketinin 500 kB eşiğini geçtiğine dair performans
uyarısı veriyor; işlev hatası değildir. Sayfalar büyüdüğünde rota bazlı dinamik
yükleme ile F aşamasında küçültülebilir.

Codex'in gömülü tarayıcı erişim ana bilgisayarı bu bilgisayarda kullanılamadığı için
otomatik ekran görüntüsü testi yapılamadı. Kullanıcı paneli `PROJEYI_BASLAT.cmd` ile
açtığında giriş ekranını doğrudan görebilir. Bu sınırlama kod, API ve üretim derleme
kontrollerini etkilemez.

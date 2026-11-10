# Zamansal ihlal-adayı kararı — E1

Modelin veya kural motorunun tek karede ürettiği `ihlal adayı`, doğrudan olay ya
da bildirim değildir. E1 aynı kişi ve ekipman için birden fazla zamanlı gözlemi
biriktirerek adayın yeterli kanıta ulaşıp ulaşmadığını belirler.

## Durum anahtarı

Kanıt şu dört alanın birleşimine aittir:

1. kamera/video oynatma oturumu;
2. olay anındaki kural sürümü;
3. yalnız bu oturum içinde anlamlı kişi takip numarası;
4. ekipman kodu.

Oturum, kişi, ekipman veya kural değiştiğinde eski sayım kullanılmaz. Takip
numarası çalışan kimliği olarak yorumlanmaz.

## Başlangıç politikası

| Eşik | Değer | Amaç |
|---|---:|---|
| Asgari ihlal-adayı gözlem | 4 | Tek/iki hatalı kareyi elemek |
| Asgari ilk–son gözlem süresi | 1,5 sn | Çok hızlı dört karenin aday olmasını engellemek |
| Kayan gözlem penceresi | 3,0 sn | Çok eski kanıtı kullanmamak |
| İki ihlal gözlemi arasındaki azami boşluk | 1,0 sn | Seyrek ve kopuk gözlemi birleştirmemek |
| Kullanılmayan durum belleği | 10,0 sn | Takip belleğinin sınırsız büyümesini önlemek |

Bu değerler hedeflenen 5–10 analiz FPS için başlangıçtır. Dört gözlem şartı kare
düşmesine tolerans bırakırken 1,5 saniye şartı aynı anda çok sayıda hızlı kareyi
yanlış güvence saymaz. Gerçek kamera açısı, örtülme ve sahaya göre yeniden
ölçülmesi gerekir.

## Değerlendirme davranışı

- `violation_candidate`: pencereye bir kanıt ekler. Sayı ve süre birlikte
  yeterliyse aday hazır olur.
- `unassessable`: ihlal sayısını artırmaz. Son ihlal gözleminden itibaren boşluk
  1 saniyeyi aşmadıysa kısa örtülmede kanıtı korur; aşarsa düşürür.
- `compliant`: birikmiş kanıtı sıfırlar.

Eşiğe ilk geçişte `became_candidate=true` yalnız bir kez döner. Sonraki kötü
kareler adayın hâlâ hazır olduğunu belirtir ancak yeni aday geçişi üretmez. Kalıcı
olayın açılması, birleştirilmesi ve kapanması E2 sorumluluğudur.

## Kontrollü deney

`scripts/evaluate_temporal_policy.py` çıktısı:

| Senaryo | Son kanıt | Aday |
|---|---:|---|
| Tek kötü kare | 1 kare / 0,0 sn | Hayır |
| 0,3 saniyede dört kötü kare | 4 kare / 0,3 sn | Hayır |
| 1,5 saniyede sürekli dört kare | 4 kare / 1,5 sn | Evet |
| Arası 1 saniyeyi aşan seyrek kareler | Son dizide 2 kare / 0,5 sn | Hayır |
| Kısa değerlendirilemiyor aralığı | 4 ihlal gözlemi / 1,5 sn | Evet |
| Üç kötü kareden sonra uygun gözlem | Yeni dizide 1 kare / 0,0 sn | Hayır |

Deney, durum makinesinin yazılım davranışını doğrular; modelin gerçek sahadaki
doğruluğunu veya dört gözlemin iş güvenliği açısından evrensel eşik olduğunu
kanıtlamaz.

## Test kapsamı

- tek kare ve hızlı kare reddi;
- süreli adayın yalnız bir kez oluşması;
- büyük boşluk, kısa/uzun belirsizlik ve uygunlukla sıfırlama;
- oturum, kural, takip ve ekipman ayrımı;
- geriye giden veya geçersiz zamanın reddi;
- eski belleğin ve biten oturumun temizlenmesi;
- geçerli/geçersiz özel politika değerleri.

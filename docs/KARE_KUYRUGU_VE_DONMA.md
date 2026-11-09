# Sınırlı Kare Kuyruğu ve Donma Durumu — C4

## Neden sınırlı kuyruk?

Kamera saniyede 30 kare üretirken model daha yavaş çalışırsa bütün kareleri
saklamak gecikmeyi ve RAM kullanımını sürekli artırır. Güvenlik panelinde beş
dakika önceki görüntüyü analiz etmek yerine güncel görüntüye yakın kalmak daha
anlamlıdır.

`LatestFrameQueue` varsayılan olarak yalnız iki kare tutar. Kuyruk doluyken yeni
kare geldiğinde en eski kare düşürülür. Bu kayıp gizlenmez; `dropped_count`
sayacına eklenir.

## İzlenen bilgiler

- etkin kamera/video oturum kimliği,
- kuyruktaki kare sayısı ve kapasite,
- alınan, işlenen ve düşürülen kare sayıları,
- son karenin alındığı UTC zamanı,
- son analizin tamamlandığı UTC zamanı,
- son görüntünün yaşı,
- son karenin alınmasından işlenmesine kadar geçen süre.

## Durumlar

| Durum | Anlamı |
|---|---|
| `idle` | Oturum açık fakat henüz kare gelmedi. |
| `healthy` | Güncel kare geliyor ve kuyruk dolu değil. |
| `backlog` | Kuyruk kapasiteye ulaştı; analiz kaynak kadar hızlı değil. |
| `stale` | Son kare belirlenen süreden eski; görüntü donmuş olabilir. |
| `stopped` | Kuyruk/oturum kapatıldı. |

Yeni oturum başladığında eski kare ve sayaçlar temizlenir. Başka oturumdan kare
eklenemez. Böylece kamera yeniden bağlandığında eski görüntü yeni takip akışına
sızmaz.

Bu aşama kuyruk ve sağlık durumunun çekirdeğidir. API/panel gösterimi F6'da,
analiz süreciyle sürekli üretici–tüketici çalışması sonraki bütünleştirmede
bağlanacaktır.

# Olay inceleme kararı ve değişiklik geçmişi — E5

Bu aşama teknik tespit ile insan kararını birbirinden ayırır. Kameranın ürettiği
`active/ended` teknik durumu değişmez; İSG görevlisi görüntüyü inceleyip olay için
ayrı bir karar verir:

- `pending`: henüz karar verilmedi veya yeniden inceleme gerekiyor;
- `confirmed`: ihlal insan tarafından doğrulandı;
- `false_alarm`: görüntü incelendi ve ihlal olmadığına karar verildi.

## Eklemeli geçmiş

`POST /api/v1/events/{event_id}/reviews` her çağrıda yeni bir
`event_review_revision` satırı oluşturur. Önceki satır güncellenmez veya silinmez.
Kayıtta şunlar bulunur:

- olay içindeki artan revizyon numarası;
- önceki ve yeni karar;
- zorunlu açıklama;
- kararı veren kullanıcı;
- UTC kayıt zamanı.

Olay satırı işlem sırasında kilitlendiği için aynı anda iki karar gelirse aynı
revizyon numarasını alamaz. Güncel `safety_event.review_status` hızlı listeleme
için son kararı taşır; denetim kaynağı revizyon geçmişidir.

`GET /api/v1/events/{event_id}/reviews` geçmişi eskiden yeniye sıralı verir. İSG
görevlisinin adı da gösterilir. Silme veya geçmiş satırını değiştirme API'si yoktur.

## Güvenlik ve bildirim

Karar yazma işlemi geçerli admin/İSG oturumuna ek olarak CSRF cookie + başlık
eşleşmesi ister. Tarayıcı başka bir siteden kullanıcı adına karar gönderemez.
Her karar, E4 `event_change` tablosuna güncel durum ve revizyon numarasıyla yeni
bir `event_updated` kaydı ekler; açık paneller olayı yeniden okuyabilir.

## Sayım kuralı

Çalışan özetindeki doğrulanmış ihlal sayısı yalnız güncel durumu `confirmed` olan
olayları sayar. `pending` ve `false_alarm` ayrı sayılır. Bu nedenle önce doğrulanıp
sonra yanlış alarm olarak düzeltilen olay doğrulanmış ihlal sayısında kalmaz. Sistem
otomatik ceza veya çalışan performans puanı üretmez.

## Doğrulama

Gerçek PostgreSQL deneyinde:

1. CSRF başlığı olmadan gönderilen karar 403 ile reddedildi.
2. Açıklamayla `pending → confirmed` revizyonu oluşturuldu.
3. Yakın inceleme gerekçesiyle `confirmed → false_alarm` düzeltmesi eklendi.
4. Geçmiş uç noktası 1 ve 2 numaralı iki revizyonu doğru önceki/yeni durumlarla
   döndürdü.
5. Olay listesi son durumu `false_alarm` gösterdi; ilk karar geçmişte kaldı.

Bu aşama API ve kalıcı kayıt katmanını tamamlar. Karar formu, geçmiş zaman çizelgesi
ve medya inceleme deneyimi F4 web paneli görevinde görünür hale getirilecektir.

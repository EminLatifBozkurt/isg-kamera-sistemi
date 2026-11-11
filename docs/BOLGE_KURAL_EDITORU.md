# Bölge kural editörü

Kamera ayrıntı ekranında gerçek API ile çalışan bir kural editörü bulunur. İSG
görevlisi kameranın tamamı için zorunlu ekipmanları seçebilir veya görüntü üzerinde
özel bölgeler çizebilir. Ekipman listesi serbest metin değildir; sistemin desteklediği
baret, yelek, gözlük, eldiven ve iş ayakkabısı kataloğundan gelir.

## Kullanım akışı

1. **Kameralar** sayfasından bir kameranın ayrıntısı açılır.
2. Her yerde geçerli ekipmanlar **Kameranın genel şartları** bölümünden seçilir.
   Ofis gibi bir yerde bu alan boş bırakılabilir.
3. Özel alan için görüntüye sırayla en az üç kez tıklanır. Son nokta geri alınabilir
   veya çizim tamamen temizlenebilir.
4. Bölge adı ve ek zorunlu ekipmanlar seçilip **Bölgeyi ekle** denir.
5. **Yeni kural sürümünü kaydet** düğmesi bütün taslağı sunucuya gönderir.

Mevcut bölge **Düzenle** ile çizim alanına geri alınabilir. Eski kural satırı ezilmez.
Her kayıt yeni, değiştirilemez bir kural sürümü oluşturur; geçmiş olay o anda geçerli
olan kurala bağlı kalır.

## Koordinat ve şekil koruması

Noktalar piksel olarak değil, görüntü genişliği ve yüksekliğine bölünmüş `0–1`
koordinatlarıyla saklanır. Görüntünün ortası çözünürlükten bağımsız `(0.5, 0.5)`
değeridir. Editör görüntünün doğal en-boy oranını kullandığı için boş kenarlar çizim
koordinatına katılmaz.

Arayüz; üçten az nokta, aynı noktanın tekrarı, sıfır alan ve kendi kendini kesen
çizgiler için erken uyarı verir. Güvenlik yalnız tarayıcıya bırakılmaz: sunucu aynı
kontrolleri tekrar yapar ve geçersiz isteği `422` ile reddeder.

## Doğrulama

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build

cd ..
node --experimental-strip-types scripts/verify_rule_geometry.ts
python scripts/verify_management_flow.py
```

Geometri deneyi farklı çizim ölçeklerinde aynı noktanın aynı normalize koordinatı
verdiğini, kenarların `0` ve `1` olduğunu ve kesişen şeklin reddedildiğini denetler.
Yönetim akışı gerçek PostgreSQL üzerinde sürüm oluşturma ve geçmişi korumayı sınar.

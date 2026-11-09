# Çoklu Kaynak Kapasitesi — C5

## Ölçüm amacı

İkinci kamerayı desteklediğimizi söylemeden önce aynı bilgisayarda iki bağımsız
PPE+ByteTrack akışının hızını ve GPU belleğini ölçmek amaçlandı. Hedef, ilk sürüm
için kaynak başına en az 5 FPS olarak seçildi; bu değer yasal veya endüstriyel
bir güvenlik standardı değildir.

## Ortam ve yöntem

- GPU: NVIDIA GeForce RTX 3050 Ti Laptop GPU
- Model: temiz veriyle eğitilen YOLO26n PPE modeli
- Görüntü boyutu: 640 piksel
- Kaynak: tam vücut PPE görüntüsünden üretilmiş kısa yerel video
- Isınma: kaynak başına 3 kare
- Ölçüm: kaynak başına 12 kare
- Takip: her kaynak için bağımsız ByteTrack/model örneği

## Sonuç

| Kaynak | Toplam FPS | Kaynak başına en düşük FPS | Ortalama takip çağrısı | Tepe ayrılmış GPU |
|---:|---:|---:|---:|---:|
| 1 | 73,612 | 73,612 | 11,390 ms | 65,197 MiB |
| 2 | 69,969 | 34,985 | 12,055 ms | 83,062 MiB |

İki kaynak da 5 FPS hedefini geçti. Bu nedenle ilk sürümün yapılandırma sınırı
**en fazla iki eşzamanlı kaynak** olarak belirlendi. Yalnız ikiye kadar ölçüm
yapıldığı için üç veya daha fazla kaynak hakkında destek iddiası yoktur.

## Ağ kamerası kararı

Öğrenci ortamında erişilebilen gerçek bir RTSP kamera bulunmadığından ağ
gecikmesi, kimlik doğrulama, bağlantı kopması ve yeniden bağlanma ölçülemedi.
Bu nedenle RTSP/ağ akışı şimdilik etkinleştirilmez. Desteklenen demo kaynakları
kayıtlı video ve yerel webcam olarak kalır.

## Sınırlar

Kısa ve kontrollü video, gerçek kalabalık fabrika görüntüsünden daha kolaydır.
Sonuç; disk kaydı, web önizleme, olay klibi ve veritabanı yükünü içermez. Sistem
bütünleştikçe H4 aşamasında uçtan uca ölçüm tekrarlanacaktır.

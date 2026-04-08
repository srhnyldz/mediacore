# Step 01 - Bootstrap

## Bu adimda yapilanlar
- Surum dosyasi, changelog ve temel teknik dokumanlar olusturuldu
- FastAPI uygulama iskeleti ve v1 task endpoint'leri eklendi
- Celery konfigrasyonu, download task'i ve convert task stub'u yazildi
- Docker Compose ile `api`, `worker`, `redis` servisleri ayrik olarak tanimlandi
- Worker imajina `ffmpeg` eklendi
- Temel test dosyalari ve sentaks dogrulama zemini kuruldu

## Sonraki adimda yapilacaklar
- Gercek ortamda bagimliliklar kurularak testler kosulacak
- Gerekirse platform bazli indirme opsiyonlari sertlestirilecek
- Donusturme hattinin ilk islevsel versiyonu tasarlanacak

## Notlar
- Bu adim sonunda surum `v0.1.0` olarak alinmistir.
- Commit ve push islemleri kullanici onayina bagli tutulacaktir.


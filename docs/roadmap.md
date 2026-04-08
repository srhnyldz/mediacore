# YLZ MediaCore Roadmap

## Faz 1 - Bootstrap ve Download Core
- API, worker ve Redis docker orkestrasyonunu kur
- Download queue ve task durum takibini calisir hale getir
- Temel test ve dokumantasyon omurgasini olustur
- Surum cizgisini `v0.1.0` ile baslat

## Faz 2 - Converter Core
- Upload tabanli `convert_task` image ve PDF donusumleri icin olgunlastirilacak
- Donusturme profilleri, dosya tipi dogrulama ve cikti paketleme stratejileri gelistirilecek
- Yeni converter tipleri ve gerekiyorsa ofis/dokuman donusum motorlari eklenecek

## Faz 3 - Storage ve Delivery
- Gecici dosya temizleme gorevleri eklenecek
- Harici obje depolama uyumu dusunulecek
- Kullanicinin indirebilecegi guvenli dosya sunum katmani tasarlanacak

## Faz 4 - SaaS Katmani
- Kimlik dogrulama ve tenant yapisi eklenecek
- Plan / kota mekanizmalari eklenecek
- Gozlemlenebilirlik, loglama ve metrik katmani genisletilecek

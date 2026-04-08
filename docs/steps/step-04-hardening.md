# Step 04 - Production Hardening

## Bu adimda yapilanlar
- Download olusturma endpoint'i icin Redis tabanli basit rate limit korumasi eklendi
- `health` yanina Redis ve ortak storage kontrolu yapan `ready` endpoint'i eklendi
- Celery tarafina task soft/hard time limit, visibility timeout ve worker recycle ayarlari tanimlandi
- Gecici indirme klasorlerini temizleyen bakim servisi, Celery task'i ve script giris noktasi eklendi
- Docker Compose icine `api` ve `redis` healthcheck tanimlari eklendi
- Cleanup akisi yerel ve container icinde tekrar kullanilabilir hale getirildi

## Sonraki adimda yapilacaklar
- Gercek `convert_task` akisina gecmek
- Signed delivery veya obje depolama stratejisini netlestirmek
- Tenant, kota ve kalici kullanici katmanina gecmek

## Notlar
- Cleanup isi su an scheduler'a bagli degil; Coolify cron ya da harici zamanlayici ile tetiklenmeye hazir.
- Rate limit ayarlari `.env` uzerinden degistirilebilir durumdadir.
- Bu adim kullanici onayi ile `v0.4.0` olarak surumlendirildi.

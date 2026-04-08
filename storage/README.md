# Storage Notes

Bu klasor repoda yalnizca paylasilan indirme alaninin amacini belgelemek icin tutulur.

- Docker ortaminda gercek dosyalar named volume olarak `/tmp/downloads` altina yazilir.
- Worker her gorev icin `/tmp/downloads/<task_id>/` klasoru olusturur.
- Ileride cron veya background cleanup gorevi bu dizinleri yaslandirarak silebilir.


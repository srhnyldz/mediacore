# Step 05 - Converter Core

## Bu adimda yapilanlar
- `convert_task` upload tabanli image/PDF donusum akisina baglandi
- Dosya upload alan `POST /api/v1/tasks/conversions` endpoint'i eklendi
- Download ve convert task durumlari `task_kind` ile ayirt edilebilir hale getirildi
- Sonuc metadata yapisina `source_file_name`, `conversion_type` ve `generated_files_count` alanlari eklendi
- Ust menulu ayrik `/convert` sayfasi ve conversion type secimi ile upload UI akisi eklendi
- Runtime smoke ile `image -> png` ve `pdf -> jpg` akislari gercek container ortaminda dogrulandi

## Sonraki adimda yapilacaklar
- Yeni converter tipleri ve ofis/dokuman donusum secenekleri eklemek
- Buyuk dosyalar icin daha guvenli upload limitleri ve dosya tarama kontrolleri eklemek
- UI tarafinda converter tipine gore ornekler, dosya sinirlari ve sonuc onizlemesi sunmak

## Notlar
- Image converter su an `jpg/jpeg/png/webp -> jpg/png/webp` matrisini destekler.
- PDF converter su an `pdf -> jpg/png` matrisini destekler; cok sayfali PDF sonucunda `.zip` paketi uretilir.
- Runtime smoke sirasinda `sample-input.jpg -> sample-input.png` ve `sample-doc.pdf -> sample-doc-page-001.jpg` basariyla uretildi.
- Bu adim `v0.5.0` olarak surumlendirildi.

# Changelog

Bu proje [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) yaklaşımına benzer sade bir format kullanır.

## [0.3.0] - 2026-04-08

### Fixed
- Applied `output_format` selections inside the worker download pipeline instead of always returning the extractor's original extension.
- Changed the default web panel output format from implicit original output to explicit `AVI`.
- Improved downloaded file resolution so converted media files are preferred over `.webp` thumbnails and other byproducts.
- Replaced brittle video postprocessing with explicit FFmpeg conversion so `AVI` downloads also complete for split-stream sources such as YouTube AV1 video plus Opus audio.
- Optimized `WEBM` output handling to prefer native WebM streams first, avoiding long-running conversions that looked stuck in the UI.

### Added
- FastAPI icinden servis edilen tek sayfa web kontrol paneli eklendi.
- Task submit, polling, sonuc metadata ve hata gosterimi icin frontend MVP tamamlandi.
- Basarili gorevler icin dogrudan dosya indirme endpoint'i ve UI linki eklendi.
- Step 03 runtime smoke ve web MVP dokumani eklendi.
- Clean Docker state ile direct MP4 smoke dogrulamasi kayda alindi.

### Changed
- Celery queue exchange ve routing key tanimlari `download` ve `convert` kuyruklari icin netlestirildi.
- Worker Docker imajina `ca-certificates` eklenerek HTTPS tabanli indirme ortamı sertlestirildi.

## [0.2.0] - 2026-04-08

### Added
- MIT `LICENSE` dosyasi eklendi.
- Ingilizce `README.md` olusturuldu ve yasal uyari eklendi.
- `Makefile` ile local venv, install, test, compile, smoke ve compose komutlari eklendi.
- Standart kutuphane kullanan API smoke script'i eklendi.
- Downloader task davranisini kapsayan ek testler ve Step 02 dokumani eklendi.

## [0.1.0] - 2026-04-08

### Added
- FastAPI tabanli temel API iskeleti eklendi.
- Celery + Redis ile ayrik worker mimarisi kuruldu.
- `yt-dlp` ve `ffmpeg` hazir Docker altyapisi tanimlandi.
- Gorev, surum ve yol haritasi dokumantasyonu baslatildi.
- Temel test iskeleti ve sentaks dogrulama akisi eklendi.

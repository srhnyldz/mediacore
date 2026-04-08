# YLZ MediaCore Proje Tanimi

## Amac
YLZ MediaCore, sosyal medya platformlarindan video ve resim indirip ilerleyen fazlarda format donusturebilen, SaaS'a evrilebilecek bir backend temelidir.

## Faz 1 Hedefleri
- FastAPI ile istek kabul eden ayrik bir API katmani kurmak
- Celery + Redis ile stateless worker mimarisi olusturmak
- `yt-dlp` tabanli indirme akisini calistirmak
- Worker imajinda `ffmpeg` kurulu olacak sekilde Docker altyapisini hazirlamak
- Her gorevi kendi klasorunde isleyip sonucunu Redis uzerinden izlenebilir kilmak

## Mimari Ozeti
- `api`: Yalnizca HTTP isteklerini alir, dogrular ve queue'ya yollar
- `worker`: Redis queue'dan gorev ceker, indirme ve ileride donusturme yapar
- `redis`: Broker ve sonuc backend katmani olarak kullanilir
- `downloads_data` volume: API ve worker tarafindan ortak gorulen gecici depolama alanidir

## Ana Tasarim Kararlari
- API ve worker ayni container ya da process icinde calismaz
- Worker'lar stateless kalir; kalici gorev durumu Redis result backend'de tutulur
- Gorev kuyruklari simdiden `download` ve `convert` olarak ayrilir
- Her gorev `/tmp/downloads/<task_id>/` altinda izole calisir
- Download olusturma akisinda Redis tabanli basit bir rate limit korumasi bulunur
- Gecici dosyalar ayrik bir cleanup isi ile periyodik olarak temizlenmeye hazir yapidadir

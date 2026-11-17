# cPanel Otomatik Let's Encrypt SSL (Docker — Sıfır FTP)

Bu proje, paylaşımlı **cPanel** hostinglerde (ör. Natro) **AutoSSL'in kapalı olduğu** durumlarda ücretsiz **Let's Encrypt SSL** sertifikasını **3 ayda bir elle uğraşmadan** otomatik olarak almak, yenilemek ve cPanel'e yüklemek için hazırlanmıştır.

FTP şifresi veya ek eklenti gerektirmez; cPanel'in kendi **API Token**'ı üzerinden hem doğrulama dosyasını web dizinine yükler hem de sertifikayı sunucuya kurar.

---

## Sistem Nasıl Çalışır? (Akış Şeması)

```text
+-----------------------------------------------------------------------+
|  Sizin Bilgisayarınız / Sunucunuz (Docker: natro-ssl-bot)             |
|                                                                       |
|  [entrypoint.sh] ---> Her 12 saatte bir "certbot renew" çalıştırır    |
|         |                                                             |
|         +--> 1. Doğrulama gerekir (süre < 30 gün veya ilk kurulum)    |
|         |       |                                                     |
|         |       v                                                     |
|         |    [auth.sh -> cpanel_api.py auth]                          |
|         |       |  HTTPS (:2083) Fileman/save_file_content            |
|         |       +----------------------------------------------+      |
|         |                                                      |      |
|         |    2. Let's Encrypt HTTP-01 ile doğrular             |      |
|         |       |  http://alanadiniz.com/.well-known/...       |      |
|         |       v                                              v      |
|         |    +---------------------+                 +-------------+  |
|         |    |   Let's Encrypt     | -- HTTP GET --> |   cPanel    |  |
|         |    |   Sunucuları        |                 | public_html |  |
|         |    +---------------------+                 +-------------+  |
|         |       |                                              ^      |
|         |       |  Doğrulama başarılı                          |      |
|         |       v                                              |      |
|         |    [cleanup.sh -> cpanel_api.py cleanup]             |      |
|         |       |  HTTPS (:2083) Fileman::fileop (unlink)      |      |
|         |       +----------------------------------------------+      |
|         |                                                      |      |
|         +--> 3. Yeni sertifika üretildi!                       |      |
|                 |                                              |      |
|                 v                                              |      |
|              [deploy.sh -> cpanel_api.py deploy]               |      |
|                 |  HTTPS (:2083) SSL/install_ssl               |      |
|                 +----------------------------------------------+      |
+-----------------------------------------------------------------------+
```

---

## Başlamadan Önce: Hostinginiz Bu Yöntemi Destekliyor mu?

Projeyi kurmadan önce cPanel hesabınızda gerekli API uç noktalarının açık olduğunu **tarayıcıdan ve terminalden** 2 dakikada doğrulayın.

### Adım 0: Sunucu Adresinizi ve Oturum Kodunuzu Bulun
cPanel'e giriş yaptığınızda tarayıcı adres çubuğu şuna benzer:
```text
https://cpls12.srvpanel.com:2083/cpsess1234567890/frontend/...
```
Buradan iki bilgiyi not alın:
* **`CPANEL_HOST`**: `cpls12.srvpanel.com` (`:2083` öncesindeki sunucu adı)
* **Oturum ön eki**: `/cpsess1234567890`

---

### Kontrol 1: AutoSSL Zaten Açık mı? (Belki Docker'a Gerek Yoktur)
Oturumunuz açıkken tarayıcıda şu adresi açın:
```text
https://<CPANEL_HOST>:2083/<cpsess_kodu>/execute/SSL/get_autossl_problems
```
* `"status": 1` dönüyorsa cPanel'in kendi **AutoSSL** özelliği hesabınızda açıktır; bu projeye ihtiyacınız olmayabilir.
* `"You do not have the feature “autossl”."` hatası alıyorsanız AutoSSL kapalıdır — **devam edin.**

---

### Kontrol 2: SSL Modülü Açık mı + Kullanıcı Adı ve Dizin Öğrenme
Tarayıcıda şu adresi açın:
```text
https://<CPANEL_HOST>:2083/<cpsess_kodu>/execute/SSL/installed_hosts
```
* `"status": 1` dönüyorsa SSL kurulum API'si açıktır.
* Çıktıdaki `"docroot"` alanından web kök dizininizi ve cPanel kullanıcı adınızı görün (ör. `"/home/u1234567/public_html"` → kullanıcı adı: **`u1234567`**).

---

### Kontrol 3: API Token Oluşturabiliyor musunuz?
Tarayıcıda şu adresi açın:
```text
https://<CPANEL_HOST>:2083/<cpsess_kodu>/execute/Tokens/list
```
* `"status": 1` dönüyorsa token oluşturma yetkiniz vardır. Yeni bir token üretmek için şu adresi açın:
```text
https://<CPANEL_HOST>:2083/<cpsess_kodu>/execute/Tokens/create_full_access?name=acme_ssl
```
Dönen JSON içindeki `"token": "..."` değerini kopyalayın ve **kimseyle paylaşmayın**.

---

### Kontrol 4: Dışarıdan Token ile `:2083` Portuna Erişebiliyor musunuz?
Bilgisayarınızda PowerShell (veya terminal) açıp aşağıdaki komutu çalıştırın:

```powershell
curl.exe -s "https://<CPANEL_HOST>:2083/execute/SSL/installed_hosts" -H "Authorization: cpanel <CPANEL_KULLANICI>:<API_TOKEN>"
```
* `"status": 1` dönüyorsa Docker dışarıdan cPanel'e bağlanıp sertifika kurabilir.

---

### Kontrol 5: Token ile Dosya Okuyup/Yazabiliyor musunuz? (`Fileman` API)
Son olarak, FTP olmadan doğrulama dosyası atabilmek için `Fileman` API'sinin açık olduğunu doğrulayın:

```powershell
curl.exe -s "https://<CPANEL_HOST>:2083/execute/Fileman/list_files?dir=%2Fhome%2F<CPANEL_KULLANICI>%2Fpublic_html" -H "Authorization: cpanel <CPANEL_KULLANICI>:<API_TOKEN>"
```
* `"status": 1` ve `public_html` içindeki dosyalar listeleniyorsa **her şey tamamdır!**
* Eğer `Fileman` kapalıysa sayfanın en altındaki **"FTP Yeteneği Olanlar İçin Uyarlama"** bölümüne bakın.

---

## Kurulum ve Çalıştırma

### 1. Ortam Değişkenlerini (`.env`) Hazırlayın
`.env.example` dosyasını `.env` olarak kopyalayın:
```powershell
Copy-Item .env.example .env
```

`.env` dosyasını açıp kendi bilgilerinizi girin:
```env
CERT_DOMAIN=alanadiniz.com
CERT_EMAIL=eposta@alanadiniz.com

CPANEL_HOST=cpls12.srvpanel.com
CPANEL_USER=u1234567
CPANEL_APITOKEN=olusturdugunuz_api_token
CPANEL_WEBROOT=/home/u1234567/public_html
```

### 2. Docker İmajını Derleyin
```powershell
docker compose build
```

### 3. Kuru Test (`--dry-run`) Yapın
Gerçek sertifika kotası harcamadan doğrulama dosyası yükleme, Let's Encrypt kontrolü ve temizlik adımlarını test edin:
```powershell
docker compose run --rm natro-ssl certonly `
  --dry-run `
  --manual `
  --preferred-challenges=http `
  --manual-auth-hook /scripts/auth.sh `
  --manual-cleanup-hook /scripts/cleanup.sh `
  --agree-tos `
  --email "eposta@alanadiniz.com" `
  --non-interactive `
  -d alanadiniz.com -d www.alanadiniz.com
```
Çıktının sonunda **`The dry run was successful.`** yazısını görmelisiniz.

### 4. İlk Gerçek Sertifikayı Alın ve cPanel'e Kurun
```powershell
docker compose run --rm natro-ssl certonly `
  --manual `
  --preferred-challenges=http `
  --manual-auth-hook /scripts/auth.sh `
  --manual-cleanup-hook /scripts/cleanup.sh `
  --deploy-hook /scripts/deploy.sh `
  --agree-tos `
  --email "eposta@alanadiniz.com" `
  --non-interactive `
  -d alanadiniz.com -d www.alanadiniz.com
```
Bu adım sertifikayı `./letsencrypt` klasörüne kaydeder ve `deploy.sh` aracılığıyla doğrudan cPanel'e yükler.

### 5. Arka Plan Otomasyonunu Başlatın
```powershell
docker compose up -d
```
Konteyner arka planda çalışır, her **12 saatte bir** uyanıp sertifika süresini kontrol eder. Sürenin dolmasına **30 günden az** kaldığında yeni sertifikayı alıp otomatik olarak cPanel'e kurar.

### Yararlı Komutlar
* **Logları izlemek için:** `docker compose logs -f natro-ssl`
* **Durumu görmek için:** `docker compose ps`
* **Token yenilemek için:** cPanel oturumunuzda `Tokens/revoke?name=acme_ssl` ardından `Tokens/create_full_access?name=acme_ssl` çağırıp `.env` dosyasını güncelleyin ve `docker compose up -d --force-recreate` çalıştırın.

---

## Proje Dosya Yapısı

* `Dockerfile` — Resmi `certbot/certbot:latest` imajı üzerine scriptleri ekler.
* `docker-compose.yml` — `natro-ssl` servisini, `.env` dosyasını ve `./letsencrypt` kalıcı hacmini tanımlar.
* `scripts/entrypoint.sh` — `daemon` modunda 12 saatlik yenileme döngüsünü çalıştırır; diğer argümanları doğrudan `certbot`'a iletir.
* `scripts/cpanel_api.py` — `auth`, `cleanup` ve `deploy` işlemlerini cPanel UAPI / API2 üzerinden gerçekleştirir.
* `scripts/auth.sh`, `scripts/cleanup.sh`, `scripts/deploy.sh` — Certbot hook çağrı sarmalayıcıları.

---

## FTP Yeteneği Olanlar İçin Uyarlama (İsteğe Bağlı)

Eğer hostinginizde `Fileman` API kapalıysa veya doğrulama dosyasını **FTP** üzerinden yüklemeyi tercih ediyorsanız, projenin sadece dosya yükleme/silme kısmını (`auth` ve `cleanup`) değiştirmeniz yeterlidir; `deploy.sh` (cPanel'e SSL kurma) kısmı aynı kalabilir.

Değiştirmeniz gereken 3 yer:

1. **`Dockerfile`**: Alpine paket yöneticisiyle `lftp` kurun:
   ```dockerfile
   FROM certbot/certbot:latest
   RUN apk add --no-cache lftp
   ...
   ```

2. **`.env.example` ve `.env`**: FTP bağlantı bilgilerini ekleyin:
   ```env
   FTP_HOST=ftp.alanadiniz.com
   FTP_USER=ftp_kullanici_adiniz
   FTP_PASS=ftp_sifreniz
   FTP_WEBROOT=/public_html
   ```

3. **`scripts/auth.sh` ve `scripts/cleanup.sh`**: `cpanel_api.py` yerine `lftp` kullanacak şekilde güncelleyin:
   * `scripts/auth.sh`:
     ```sh
     #!/bin/sh
     set -eu
     TMP_FILE="$(mktemp)"
     trap 'rm -f "${TMP_FILE}"' EXIT
     printf '%s' "${CERTBOT_VALIDATION}" > "${TMP_FILE}"

     lftp -u "${FTP_USER},${FTP_PASS}" "${FTP_HOST}" <<EOF
     set ssl:verify-certificate no
     mkdir -p -f "${FTP_WEBROOT}/.well-known/acme-challenge"
     put "${TMP_FILE}" -o "${FTP_WEBROOT}/.well-known/acme-challenge/${CERTBOT_TOKEN}"
     bye
     EOF
     ```
   * `scripts/cleanup.sh`:
     ```sh
     #!/bin/sh
     set -eu
     lftp -u "${FTP_USER},${FTP_PASS}" "${FTP_HOST}" <<EOF
     set ssl:verify-certificate no
     rm -f "${FTP_WEBROOT}/.well-known/acme-challenge/${CERTBOT_TOKEN}"
     bye
     EOF
     ```

*(Eğer cPanel API Token özelliğiniz de tamamen kapalıysa, `scripts/deploy.sh` içindeki `cpanel_api.py deploy` çağrısını bir Telegram/e-posta bildirim scriptiyle değiştirip yenileme olduğunda sertifikayı panelden elle yapıştırabilirsiniz.)*

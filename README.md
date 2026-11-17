# Natro cPanel Otomatik Let's Encrypt SSL (Docker — Sıfır FTP)

Bu proje `tekfark.com.tr` ve `www.tekfark.com.tr` için Let's Encrypt SSL sertifikasını **FTP kullanmadan**, yalnızca **cPanel API Token** ile tam otomatik yönetir:
1. **Doğrulama:** cPanel `Fileman` API üzerinden `/home/u2712954/public_html/.well-known/acme-challenge/` dosyasını oluşturur ve doğrulama sonrası siler.
2. **Yenileme:** Her 12 saatte bir kontrol eder, süresi dolmadan (30 gün kala) otomatik yeniler.
3. **Kurulum:** Yenilenen sertifikayı **cPanel UAPI (`SSL/install_ssl`)** üzerinden otomatik olarak sunucuya yükler.

## Kurulum

1. `.env.example` dosyasını `.env` olarak kopyalayıp `CERT_EMAIL` ve `CPANEL_APITOKEN` değerlerini doldurun:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Docker imajını derleyin:
   ```powershell
   docker compose build
   ```

3. Önce kuru test (`--dry-run`) ile doğrulama akışını test edin:
   ```powershell
   docker compose run --rm natro-ssl certonly `
     --dry-run `
     --manual `
     --preferred-challenges=http `
     --manual-auth-hook /scripts/auth.sh `
     --manual-cleanup-hook /scripts/cleanup.sh `
     --agree-tos `
     --email "eposta@tekfark.com.tr" `
     --non-interactive `
     -d tekfark.com.tr -d www.tekfark.com.tr
   ```

4. Kuru test başarılıysa gerçek sertifikayı alıp cPanel'e yükleyin:
   ```powershell
   docker compose run --rm natro-ssl certonly `
     --manual `
     --preferred-challenges=http `
     --manual-auth-hook /scripts/auth.sh `
     --manual-cleanup-hook /scripts/cleanup.sh `
     --deploy-hook /scripts/deploy.sh `
     --agree-tos `
     --email "eposta@tekfark.com.tr" `
     --non-interactive `
     -d tekfark.com.tr -d www.tekfark.com.tr
   ```

5. Arka planda sürekli çalışacak otomatik yenileme konteynerini başlatın:
   ```powershell
   docker compose up -d
   ```

## Kontrol ve Güvenlik

- **Logları izlemek için:**
  ```powershell
  docker compose logs -f natro-ssl
  ```
- **API Token yenileme:** Kurulumdan sonra eski token'ı iptal edip yenisini oluşturmak isterseniz cPanel oturumunuzda `Tokens/revoke?name=acme_ssl` ardından `Tokens/create_full_access?name=acme_ssl` çağırıp `.env` dosyasını güncelleyebilirsiniz.

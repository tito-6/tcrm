# Teklif Paneli (`tcrm_offer`)

Profesyonel teklif oluşturma, public passcode paylaşımı ve immutable müşteri onayı.

## Kurulum

```bash
# Tenant DB (ör. akod_prod)
tcrm-bin -c /opt/tcrm/tcrm.prod.conf -d akod_prod -i tcrm_offer --stop-after-init
```

Public URL: `https://<host>/teklif/<opaqueToken>`

## Ayarlar

- `tcrm_offer.default_tax_rate` — varsayılan KDV (%)
- `tcrm_offer.public_base_url` — public link tabanı (örn. `https://akod.tcrm.online`)
- `tcrm_offer.token_pepper` — token hash pepper (kurulumda değiştirin)

## Akış

1. Admin şablondan veya sıfırdan teklif oluşturur
2. Yayınla → public token + passcode bir kez gösterilir
3. Müşteri `/teklif/<token>` + passcode ile girer
4. Seçim / bütçe → sunucu quote → **Teklifi Onayla**
5. Snapshot kilitlenir; admin linki kapatabilir

## Test

```bash
tcrm-bin -c tcrm.conf -d <db> -i tcrm_offer --test-enable --stop-after-init
```

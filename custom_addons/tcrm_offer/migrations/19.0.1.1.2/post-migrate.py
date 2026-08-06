# -*- coding: utf-8 -*-
"""Force-load contract HTML on AKOD digital template (noupdate xmlids ignored updates)."""
import logging

_logger = logging.getLogger(__name__)

SUMMARY = """
<p>Bu teklif; <strong>zorunlu temel paket</strong> (kurulum + reklam yönetimi + içerik/platform yönetimi)
ile isteğe bağlı ek hizmetleri içerir. Reklam medya bütçesi hizmet bedeline dahil değildir.</p>
<p>Aşağıdaki seçimlerle aylık, tek seferlik ve genel toplamı anında görebilirsiniz. Onay sonrası seçimler kilitlenir.</p>
"""

SCOPE = """
<p><strong>Zorunlu temel paket</strong> her teklifte varsayılandır:</p>
<ul>
  <li>Kurulum / hesap set-up — 50.000 TL (tek seferlik)</li>
  <li>Reklam yönetimi (Meta + Google) — bütçe ≤ 50.000 TL için 30.000 TL/ay</li>
  <li>İçerik &amp; paylaşım (IG/FB + bir ek platform) — 20.000 TL/ay</li>
</ul>
<p>Opsiyonel kalemler yalnızca seçildiğinde genel toplama eklenir.</p>
"""

INTRO = """
<section class="teklif-madde">
  <h3>MADDE 1 — Taraflar</h3>
  <p>İşbu teklif / dijital hizmet sözleşmesi taslağı; AKOD Yazılım Bilişim ve Dijital Pazarlama
  Ticaret Limited Şirketi ("Hizmet Sağlayıcı" / "AKOD") ile teklifte adı geçen Müşteri arasında
  akdedilmek üzere hazırlanmıştır.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 2 — Konu</h3>
  <p>AKOD tarafından sunulacak dijital büyüme hizmetlerinin kapsamı, ücretlendirme, hak ve
  yükümlülükler, gizlilik, fikri mülkiyet ve sona erme koşulları.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 3 — Tanımlar</h3>
  <ul>
    <li><strong>Reklam Bütçesi:</strong> Müşteri'nin Meta/Google vb. platformlara doğrudan ödediği
    medya harcaması; aylık hizmet bedeline dahil değildir.</li>
    <li><strong>Hizmet Ayı:</strong> Ücretin peşin ödendiği takvim ayı.</li>
    <li><strong>Ham Materyal:</strong> Müşteri'nin temin etmesi gereken fotoğraf, video ve marka varlıkları.</li>
  </ul>
</section>
"""

TERMS = """
<section class="teklif-madde">
  <h3>MADDE 4 — Hizmet kapsamı</h3>
  <p>Seçilen kalemlere göre Meta/Google reklam yönetimi, sosyal medya içerik ve yayın,
  raporlama/toplantı, isteğe bağlı prodüksiyon ve web/yazılım hizmetleri.</p>
  <p><strong>Önemli:</strong> Temel içerik paketinde fiziksel çekim/prodüksiyon zorunlu değildir;
  ham görseller Müşteri sorumluluğundadır (aksi seçilmedikçe).</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 5 — Başlangıç ön koşulları</h3>
  <ul>
    <li>Teklifin onaylanması / sözleşmenin imzası</li>
    <li>İlk ay bedeli + kurulum ücretinin ödenmesi</li>
    <li>Meta Business Manager / Google Ads yönetici erişimi</li>
    <li>Marka materyallerinin iletilmesi</li>
  </ul>
</section>
<section class="teklif-madde">
  <h3>MADDE 6 — Yükümlülükler</h3>
  <p><strong>AKOD:</strong> profesyonel yürütme, aylık rapor, gizlilik, erişimin yalnızca hizmet için kullanımı.</p>
  <p><strong>Müşteri:</strong> peşin ödeme, reklam bütçesini platformlara yatırma, ham materyal ve erişim,
  içerik onay sürelerine uyum, ticari koşulların gizliliği.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 7 — Ücretler ve ödeme</h3>
  <ul>
    <li>Tüm fiyatlar aksi belirtilmedikçe <strong>KDV hariçtir</strong>.</li>
    <li>Aylık bedel peşin; ilk ödeme onaydan sonra makul sürede.</li>
    <li>Reklam bütçesi hizmet bedeline dahil değildir.</li>
    <li>Gecikmede temerrüt faizi ve hizmet askıya alma hakkı saklıdır.</li>
  </ul>
</section>
<section class="teklif-madde">
  <h3>MADDE 8–10 — Reklam / sosyal / web özel hükümler</h3>
  <p>AKOD belirli ROAS, satış, takipçi veya lead taahhüt etmez; süreç ve optimizasyon sorumluluğunu üstlenir.
  Platform politikaları üçüncü taraf riskidir. Web fiyatları tech stack, sektör ve tahmini üretim saatine göre değişir.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 11–13 — Gizlilik ve fikri mülkiyet</h3>
  <p>Ticari koşullar, yöntemler ve know-how gizli tutulur. Onaylı çıktılar Müşteri'nin kendi tanıtımı için
  kullanılabilir; AKOD yöntemleri üzerinde hak iddia edilemez.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 14 — KVKK</h3>
  <p>Taraflar 6698 sayılı KVKK'ya uygun hareket eder. Aydınlatma metni teklif onayında bağlantı ile sunulur.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 15–16 — Üçüncü taraf &amp; performans reddi</h3>
  <p>Google/Meta bağımsız platformlardır. Belirli iş sonucu garantisi verilmez.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 17 — Süre ve fesih</h3>
  <p>Aylık yenilenir; 15 gün önceden yazılı bildirim ile sonraki ay itibarıyla sona erdirilebilir.
  Peşin ücretler iade edilmez.</p>
</section>
<section class="teklif-madde">
  <h3>MADDE 18–20 — Mücbir sebep, bildirim, yetkili mahkeme</h3>
  <p>Türk Hukuku uygulanır; yetkili merciler İstanbul mahkemeleri ve icra daireleridir.</p>
</section>
<p class="teklif-terms-foot">Bu metin teklif amaçlı özet hükümlerdir. Kesin sözleşme, onay sonrası
taraflarca imzalanacak nihai metinde yer alır.</p>
"""


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Allow future XML updates
    env['ir.model.data'].search([
        ('module', '=', 'tcrm_offer'),
        ('name', 'in', [
            'template_akod_dijital',
            'template_ahsen_magaza',
        ]),
    ]).write({'noupdate': False})

    tmpl = env['tcrm.offer.template'].search([('code', '=', 'akod_dijital_temel')], limit=1)
    if not tmpl:
        _logger.warning('tcrm_offer: akod_dijital_temel template missing')
        return
    tmpl.write({
        'summary': SUMMARY,
        'scope_html': SCOPE,
        'contract_intro_html': INTRO,
        'terms_html': TERMS,
        'provider_legal_name': (
            tmpl.provider_legal_name
            or 'AKOD Yazılım Bilişim ve Dijital Pazarlama Ticaret Limited Şirketi'
        ),
        'provider_short_name': tmpl.provider_short_name or 'AKOD',
    })
    cats = env['tcrm.offer.catalogue'].search([])
    if cats:
        tmpl.catalogue_ids = [(6, 0, cats.ids)]

    # Refresh open offers created from this template style
    offers = env['tcrm.offer'].search([
        ('status', 'in', ('draft', 'published', 'viewed', 'paused')),
        '|',
        ('title', 'ilike', 'Dijital Hizmet'),
        ('provider_short_name', '=', 'AKOD'),
    ])
    for offer in offers:
        if not offer.terms_html or len(offer.terms_html) < 50:
            offer.write({
                'summary': tmpl.summary,
                'scope_html': tmpl.scope_html,
                'contract_intro_html': tmpl.contract_intro_html,
                'terms_html': tmpl.terms_html,
                'catalogue_ids': [(6, 0, tmpl.catalogue_ids.ids)],
            })
    _logger.info('tcrm_offer: contract HTML seeded on template %s (%s offers)', tmpl.id, len(offers))

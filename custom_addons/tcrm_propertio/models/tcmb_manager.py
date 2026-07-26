import requests
from lxml import etree
from datetime import datetime, date
from tcrm import models, fields, api, _

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def get_tcmb_data(self, target_date=None):
        """ Returns a list of dicts from TCMB. Handles both today and history. """
        if not target_date:
            target_date = fields.Date.today()
            
        url = self._get_tcmb_url(target_date)
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return self._parse_tcmb_xml(response.content)
            else:
                return []
        except Exception:
            return []

    @api.model
    def _get_tcmb_url(self, target_date):
        if target_date == fields.Date.today():
            return "https://www.tcmb.gov.tr/kurlar/today.xml"
        
        # Historical: https://www.tcmb.gov.tr/kurlar/202301/12012023.xml
        y_m = target_date.strftime('%Y%m')
        d_m_y = target_date.strftime('%d%m%Y')
        return f"https://www.tcmb.gov.tr/kurlar/{y_m}/{d_m_y}.xml"

    @api.model
    def _parse_tcmb_xml(self, content):
        data = []
        try:
            root = etree.fromstring(content)
            for node in root.findall('Currency'):
                code = node.get('CurrencyCode')
                name = node.find('Isim').text if node.find('Isim') is not None else code
                
                # ForexBuying (Döviz Alış)
                buying = node.find('ForexBuying').text
                # ForexSelling (Döviz Satış) - User might want this too
                selling = node.find('ForexSelling').text
                
                # BanknoteBuying/Selling also exist but Forex is standard
                
                if buying: # Buying is mandatory for our base calc
                    try:
                        val_buying = float(buying)
                        val_selling = float(selling) if selling else 0.0
                        
                        data.append({
                            'code': code,
                            'name': name.strip() if name else '',
                            'buying': val_buying,
                            'selling': val_selling
                        })
                    except ValueError:
                        continue
        except Exception:
            pass
        return data

    def _update_tcmb_rates(self):
        """ Cron job entry point: Fetch today's rates and update TCRM """
        today = fields.Date.today()
        data = self.get_tcmb_data(today)
        self._apply_rates(data, today)

    @api.model
    def _apply_rates(self, data, rate_date):
        company = self.env.company
        # Logic assumes Company Base = TRY
        if company.currency_id.name != 'TRY':
            return
            
        active_currencies = self.search([('active', '=', True)])
        currency_map = {c.name: c for c in active_currencies}
        
        for row in data:
            code = row['code']
            rate_val = row['buying'] # Using Buying Rate for conversion
            
            if code in currency_map and rate_val > 0:
                tcrm_rate = 1.0 / rate_val
                currency = currency_map[code]
                
                existing = self.env['res.currency.rate'].search([
                     ('currency_id', '=', currency.id),
                     ('name', '=', rate_date),
                     ('company_id', '=', company.id)
                ], limit=1)
                
                if not existing:
                    self.env['res.currency.rate'].create({
                        'currency_id': currency.id,
                        'name': rate_date,
                        'rate': tcrm_rate,
                        'company_id': company.id
                    })
                else:
                    existing.rate = tcrm_rate

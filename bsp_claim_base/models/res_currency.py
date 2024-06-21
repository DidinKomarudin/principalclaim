from odoo import api, fields, models
import requests
from bs4 import BeautifulSoup

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.multi
    def schedule_get_current_rate(self):
        currency_ids = self.search([])
        page = requests.get('https://www.bi.go.id/id/statistik/informasi-kurs/transaksi-bi/Default.aspx')
        data = page.text
        soup = BeautifulSoup(data, "lxml")
        table_body = soup.find_all('tbody')[1]
        rows = table_body.find_all('tr')
        currencies = {}
        for row in rows:
            cols = row.find_all('td')
            cols = [x.text.strip() for x in cols]
            currencies[cols[0]] = float(cols[2].replace('.', '').replace(',', '.'))  # kurs jual

        for currency_id in currency_ids:
            if currencies.get(currency_id.name):
                self.env['res.currency.rate'].create({
                    'currency_id': currency_id.id,
                    'name': fields.Datetime.now(),
                    'rate': 1 / currencies[currency_id.name]
                })

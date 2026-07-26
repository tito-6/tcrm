from tcrm import models, fields, api, _
from tcrm.exceptions import UserError

class PropertioInstallmentReallocateWizard(models.TransientModel):
    _name = 'propertio.installment.reallocate.wizard'
    _description = 'Reallocate and Delete Installment Wizard'

    source_installment_id = fields.Many2one('propertio.installment', string='Silinecek Taksit', required=True, readonly=True)
    sale_id = fields.Many2one('propertio.sale', related='source_installment_id.sale_id', readonly=True)
    amount_to_reallocate = fields.Monetary(string='Kaydırılacak Tutar', related='source_installment_id.amount', readonly=True)
    currency_id = fields.Many2one('res.currency', related='source_installment_id.currency_id', readonly=True)
    
    target_installment_id = fields.Many2one(
        'propertio.installment', 
        string='Aktarılacak Taksit', 
        required=True,
        domain="[('sale_id', '=', sale_id), ('id', '!=', source_installment_id), ('is_paid', '=', False)]",
        help="Silinen taksitin tutarının ekleneceği diğer taksiti seçin."
    )

    def action_confirm(self):
        self.ensure_one()
        if not self.target_installment_id:
            raise UserError(_("Aktarılacak taksit seçilmedi."))
            
        if self.source_installment_id.amount_paid > 0:
            raise UserError(_("Kısmen veya tamamen ödenmiş bir taksit silinemez. Önce tahsilatları iptal edin."))

        source_name = self.source_installment_id.name
        source_amount = self.source_installment_id.amount
        target_name = self.target_installment_id.name
        target_old_amount = self.target_installment_id.amount
        
        # Add amount to target
        self.target_installment_id.amount += source_amount
        
        # Log to chatter
        self.sale_id.message_post(
            body=_("<b>Taksit Silindi ve Birleştirildi:</b> '%s' isimli taksit (%s) silindi ve tutarı '%s' isimli taksite eklendi. (Yeni Tutar: %s -> %s)") % (
                source_name, source_amount, target_name, target_old_amount, self.target_installment_id.amount
            )
        )
        
        # Securely delete source
        self.source_installment_id.with_context(force_reallocate_delete=True).unlink()
        
        return {'type': 'ir.actions.act_window_close'}

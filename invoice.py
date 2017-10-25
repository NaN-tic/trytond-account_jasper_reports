#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder
from trytond.pool import Pool

__all__ = ['NotReconciledStart', 'NotReconciled']


class NotReconciledStart(ModelView):
    'Not Reconciled Start'
    __name__ = 'account.not_reconciled.start'

    company = fields.Many2One('company.company', 'Company', required=True,
        readonly=True)
    date = fields.Date('Date', required=True)
    parties = fields.Many2Many('party.party', None, None, 'Parties')

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_date():
        pool = Pool()
        Date = pool.get('ir.date')
        return Date.today()


class NotReconciled(Wizard):
    'Not Reconciled'
    __name__ = 'account.not_reconciled'

    start = StateView('account.not_reconciled.start',
        'account_jasper_reports.not_reconciled_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'not_reconciled', 'tryton-ok', default=True),
            ])
    not_reconciled = StateAction('account_invoice.act_invoice_form')

    def do_not_reconciled(self, action):
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        domain = [('maturity_date', '<=', self.start.date),
            ('move.company', '=', self.start.company),
            ('reconciliation_date', '>=', self.start.date)]
        active_ids = Transaction().context['active_ids']
        if active_ids:
            domain.append(('origin.id', 'in', active_ids, 'account.invoice'))
        if self.start.parties:
            domain.append(('party', 'in', self.start.parties))
        move_lines = MoveLine.search(domain)
        not_reconciled_moves = [move_line.move.id for move_line in move_lines]
        action['pyson_domain'] = PYSONEncoder().encode([('move', 'in',
                    not_reconciled_moves)])
        return action, {}

# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, StateReport, Button
from trytond.pyson import Eval
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['PrintTaxesByInvoiceAndPeriodStart', 'PrintTaxesByInvoiceAndPeriod',
    'TaxesByInvoiceReport', 'TaxesByInvoiceAndPeriodReport']


class PrintTaxesByInvoiceAndPeriodStart(ModelView):
    'Print Taxes by Invoice and Period'
    __name__ = 'account_jasper_reports.print_taxes_by_invoice.start'

    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    periods = fields.Many2Many('account.period', None, None, 'Periods',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ], depends=['fiscalyear'])
    partner_type = fields.Selection([
            ('customers', 'Customers'),
            ('suppliers', 'Suppliers'),
            ], 'Party Type', required=True)
    grouping = fields.Selection([
            ('base_tax_code', 'Base Tax Code'),
            ('invoice', 'Invoice'),
            ], 'Grouping', required=True)
    totals_only = fields.Boolean('Totals Only')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    output_format = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Format', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_partner_type():
        return 'customers'

    @staticmethod
    def default_grouping():
        return 'base_tax_code'

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_output_format():
        return 'pdf'

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        self.periods = None


class PrintTaxesByInvoiceAndPeriod(Wizard):
    'Print TaxesByInvoiceAndPeriod'
    __name__ = 'account_jasper_reports.print_taxes_by_invoice'
    start = StateView('account_jasper_reports.print_taxes_by_invoice.start',
        'account_jasper_reports.print_taxes_by_invoice_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateReport('account_jasper_reports.taxes_by_invoice')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'periods': [x.id for x in self.start.periods],
            'parties': [x.id for x in self.start.parties],
            'output_format': self.start.output_format,
            'partner_type': self.start.partner_type,
            'totals_only': self.start.totals_only,
            'grouping': self.start.grouping,
            }
        if data['grouping'] == 'invoice':
            state_action = StateAction('account_jasper_reports.'
                'report_taxes_by_invoice_and_period')
            action = state_action.get_action()
        return action, data

    def transition_print_(self):
        return 'end'

    def default_start(self, fields):
        Party = Pool().get('party.party')
        party_ids = []
        if Transaction().context.get('model') == 'party.party':
            for party in Party.browse(Transaction().context.get('active_ids')):
                party_ids.append(party.id)
        return {
            'parties': party_ids,
            }


class TaxesByInvoiceReport(JasperReport):
    __name__ = 'account_jasper_reports.taxes_by_invoice'

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        Company = pool.get('company.company')
        FiscalYear = pool.get('account.fiscalyear')
        Period = pool.get('account.period')
        Party = pool.get('party.party')
        AccountInvoiceTax = pool.get('account.invoice.tax')

        fiscalyear = FiscalYear(data['fiscalyear'])
        periods = []
        if data.get('periods'):
            periods = Period.browse(data.get('periods', []))
            periods_subtitle = []
            for x in periods:
                periods_subtitle.append(x.rec_name)
            periods_subtitle = '; '.join(periods_subtitle)
        else:
            periods = Period.search([('fiscalyear', '=', fiscalyear.id)])
            periods_subtitle = ''

        with Transaction().set_context(active_test=False):
            parties = Party.browse(data.get('parties', []))
        if parties:
            parties_subtitle = []
            for x in parties:
                if len(parties_subtitle) > 4:
                    parties_subtitle.append('...')
                    break
                parties_subtitle.append(x.rec_name)
            parties_subtitle = '; '.join(parties_subtitle)
        else:
            parties_subtitle = ''

        company = None
        if data['company']:
            company = Company(data['company'])

        parameters = {}
        parameters['company'] = fiscalyear.company.rec_name
        parameters['fiscal_year'] = fiscalyear.rec_name
        parameters['parties'] = parties_subtitle
        parameters['periods'] = periods_subtitle
        parameters['TOTALS_ONLY'] = data['totals_only'] and True or False
        parameters['company_rec_name'] = company and company.rec_name or ''
        parameters['company_vat'] = (company
            and company.party.tax_identifier and
            company.party.tax_identifier.code) or ''

        domain = [('invoice.state', 'in', ['posted', 'paid'])]

        if data['partner_type'] == 'customers':
            domain += [('invoice.type', '=', 'out')]
        else:
            domain += [('invoice.type', '=', 'in')]

        if periods:
            domain += [('invoice.move.period', 'in', periods)]

        if parties:
            domain += [('invoice.party', 'in', parties)],

        report_ids = [x.id for x in AccountInvoiceTax.search(domain,
            order=[('account', 'ASC')])]
        return report_ids, parameters

    @classmethod
    def execute(cls, ids, data):
        with Transaction().set_context(active_test=False):
            report_ids, parameters = cls.prepare(data)
        return super(TaxesByInvoiceReport, cls).execute(report_ids, {
                'name': cls.__name__,
                'parameters': parameters,
                'output_format': data['output_format'],
                })


class TaxesByInvoiceAndPeriodReport(TaxesByInvoiceReport):
    __name__ = 'account_jasper_reports.taxes_by_invoice_and_period'

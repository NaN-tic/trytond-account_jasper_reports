# coding=utf-8
#This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
#at the top level of this repository contains the full copyright notices and
#license terms.
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['PrintAbreviatedJournalStart', 'PrintAbreviatedJournal',
    'AbreviatedJournalReport']


class PrintAbreviatedJournalStart(ModelView):
    'Print Abreviated Journal'
    __name__ = 'account_jasper_reports.print_abreviated_journal.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    output_type = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Type', required=True)
    display_account = fields.Selection([
            ('bal_all', 'All'),
            ('bal_movement', 'With movements'),
            ], 'Display Accounts', required=True)
    level = fields.Integer('Level', help='Display accounts of this level',
        required=True)
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_output_type():
        return 'pdf'

    @staticmethod
    def default_display_account():
        return 'bal_all'

    @staticmethod
    def default_level():
        return 1


class PrintAbreviatedJournal(Wizard):
    'Print Abreviated Journal'
    __name__ = 'account_jasper_reports.print_abreviated_journal'
    start = StateView('account_jasper_reports.print_abreviated_journal.start',
        'account_jasper_reports.print_abreviated_journal_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('account_jasper_reports.report_abreviated_journal')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'display_account': self.start.display_account,
            'level': self.start.level,
            'output_type': self.start.output_type,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class AbreviatedJournalReport(JasperReport):
    __name__ = 'account_jasper_reports.abreviated_journal'

    @classmethod
    def execute(cls, ids, data):

        pool = Pool()
        Account = pool.get('account.account')
        Period = pool.get('account.period')
        FiscalYear = pool.get('account.fiscalyear')

        fiscalyear = FiscalYear(data['fiscalyear'])
        transaction = Transaction()

        res = []
        parameters = {}
        parameters['fiscal_year'] = fiscalyear.rec_name

        # Calculate the account level
        account_ids = []
        level = data['level']
        for account in Account.search([('company', '=', data['company'])],
                order=[('code', 'ASC')]):
            if len(account.code) == level or \
                account.kind != 'view' and len(account.childs) == 0 and \
                    len(account.code) < level:
                account_ids.append(account.id)

        periods = Period.search([('fiscalyear', '=', fiscalyear)])
        for period in periods:
            with transaction.set_context(periods=[period.id]):
                for account in Account.read(account_ids,
                        ['kind', 'code', 'name', 'debit', 'credit']):

                    display = data['display_account']
                    # Check if we need to include this account
                    if display == 'bal_all' or display == 'bal_movement' and \
                            (account['debit'] != 0.0 or
                            account['credit'] != 0.0):
                        res.append({
                                'month': period.rec_name,
                                'type': account['kind'],
                                'code': account['code'],
                                'name': account['name'],
                                'debit': account['debit'],
                                'credit': account['credit'],
                            })

        return super(AbreviatedJournalReport, cls).execute(ids, {
                'name': 'account_jasper_reports.journal',
                'data_source': 'records',
                'records': res,
                'parameters': parameters,
                'output_format': data['output_type'],
                })

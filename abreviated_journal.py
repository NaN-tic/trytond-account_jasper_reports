# coding=utf-8
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from sql.aggregate import Sum
from sql.conditionals import Coalesce

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateReport, Button
from trytond.tools import reduce_ids, grouped_slice
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['PrintAbreviatedJournalStart', 'PrintAbreviatedJournal',
    'AbreviatedJournalReport']


class PrintAbreviatedJournalStart(ModelView):
    'Print Abreviated Journal'
    __name__ = 'account_jasper_reports.print_abreviated_journal.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    output_format = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Format', required=True)
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
    def default_output_format():
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
    print_ = StateReport('account_jasper_reports.abreviated_journal')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'display_account': self.start.display_account,
            'level': self.start.level,
            'output_format': self.start.output_format,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class AbreviatedJournalReport(JasperReport):
    __name__ = 'account_jasper_reports.abreviated_journal'

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        Company = pool.get('company.company')
        Account = pool.get('account.account')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')
        FiscalYear = pool.get('account.fiscalyear')
        line = MoveLine.__table__()
        move = Move.__table__()
        table_a = Account.__table__()
        table_c = Account.__table__()

        fiscalyear = FiscalYear(data['fiscalyear'])
        transaction = Transaction()
        cursor = transaction.connection.cursor()

        res = []
        parameters = {}
        parameters['company'] = fiscalyear.company.rec_name
        parameters['fiscal_year'] = fiscalyear.rec_name

        company = None
        if data['company']:
            company = Company(data['company'])
        parameters['company_rec_name'] = company and company.rec_name or ''
        parameters['company_vat'] = (company
            and company.party.tax_identifier and
            company.party.tax_identifier.code) or ''

        move_join = 'LEFT'
        if data['display_account'] == 'bal_movement':
            move_join = 'INNER'
        # Calculate the account level
        account_ids = []
        level = data['level']
        with Transaction().set_context(active_test=False):
            for account in Account.search([('company', '=', data['company'])],
                    order=[('code', 'ASC')]):
                if not account.code or not account.parent:
                    continue
                if len(account.code) == level or \
                    account.type != None and len(account.childs) == 0 and \
                        len(account.code) < level:
                    account_ids.append(account.id)
            accounts = Account.browse(account_ids)
        group_by = (table_a.id,)
        columns = (group_by + (Sum(Coalesce(line.debit, 0)).as_('debit'),
                Sum(Coalesce(line.credit, 0)).as_('credit')))
        periods = Period.search([
                ('fiscalyear', '=', fiscalyear),
                ('type', '=', 'standard'),
                ])
        for period in periods:
            all_accounts = {}
            for sub_ids in grouped_slice(account_ids):
                red_sql = reduce_ids(table_a.id, sub_ids)
                cursor.execute(*table_a.join(table_c,
                        condition=(table_c.left >= table_a.left)
                        & (table_c.right <= table_a.right)
                        ).join(line, move_join,
                            condition=line.account == table_c.id
                        ).join(move, move_join,
                            condition=move.id == line.move
                        ).select(
                            *columns,
                            where=red_sql &
                            (Coalesce(move.period, period.id) == period.id),
                            group_by=group_by))

                for row in cursor.fetchall():
                    account_id, debit, credit = row
                    if not isinstance(debit, Decimal):
                        debit = Decimal(str(debit))
                    if not isinstance(credit, Decimal):
                        credit = Decimal(str(credit))
                    all_accounts[account_id] = {
                        'debit': debit,
                        'credit': credit,
                        }
            for account in accounts:
                if account.id in all_accounts:
                    res.append({
                            'month': period.rec_name,
                            'period_date': period.start_date,
                            'code': account.code,
                            'name': account.name,
                            'debit': all_accounts[account.id]['debit'],
                            'credit': all_accounts[account.id]['credit'],
                            })
                elif data['display_account'] == 'bal_all':
                    res.append({
                            'month': period.rec_name,
                            'period_date': period.start_date,
                            'code': account.code,
                            'name': account.name,
                            'debit': Decimal('0.0'),
                            'credit': Decimal('0.0'),
                            })
        return res, parameters

    @classmethod
    def execute(cls, ids, data):
        res, parameters = cls.prepare(data)
        return super(AbreviatedJournalReport, cls).execute(ids, {
                'name': 'account_jasper_reports.journal',
                'data_source': 'records',
                'records': res,
                'parameters': parameters,
                'output_format': data['output_format'],
                })

#This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
#at the top level of this repository contains the full copyright notices and
#license terms.

from decimal import Decimal
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import Eval, Bool
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['PrintGeneralLedgerStart', 'PrintGeneralLedger',
    'GeneralLedgerReport']


class PrintGeneralLedgerStart(ModelView):
    'Print General Ledger'
    __name__ = 'account_jasper_reports.print_general_ledger.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True, on_change=['fiscalyear'])
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ], depends=['fiscalyear', 'end_period'])
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['fiscalyear', 'start_period'])
    all_accounts = fields.Boolean('All Accounts')
    accounts = fields.Many2Many('account.account', None, None, 'Accounts',
        states={
            'invisible': Bool(Eval('all_accounts')),
            'required': ~Bool(Eval('all_accounts')),
            }, depends=['all_accounts'])
    all_parties = fields.Boolean('All Parties')
    parties = fields.Many2Many('party.party', None, None, 'Parties',
        states={
            'invisible': Bool(Eval('all_parties')),
            'required': ~Bool(Eval('all_parties')),
            }, depends=['all_parties'])
    output_type = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Type', required=True)
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
    def default_all_accounts():
        return True

    @staticmethod
    def default_all_parties():
        #TODO: Check that the wizard works if executed from party view
        print "CONTEXT: ", Transaction().context
        if Transaction().context.get('model') == 'party.party':
            return False
        return True

    @staticmethod
    def default_output_type():
        return 'pdf'

    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }


class PrintGeneralLedger(Wizard):
    'Print GeneralLedger'
    __name__ = 'account_jasper_reports.print_general_ledger'
    start = StateView('account_jasper_reports.print_general_ledger.start',
        'account_jasper_reports.print_general_ledger_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('account_jasper_reports.report_general_ledger')

    def do_print_(self, action):
        start_period = None
        if self.start.start_period:
            start_period = self.start.start_period.id
        end_period = None
        if self.start.end_period:
            end_period = self.start.end_period.id
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'start_period': start_period,
            'end_period': end_period,
            'accounts': [x.id for x in self.start.accounts],
            'parties': [x.id for x in self.start.parties],
            'output_type': self.start.output_type,
            }
        return action, data

    def transition_print_(self):
        return 'end'

    def default_start(self, fields):
        Party = Pool().get('party.party')
        account_ids = []
        party_ids = []
        if Transaction().context.get('model') == 'party.party':
            for party in Party.browse(Transaction().context.get('active_ids')):
                if party.account_payable:
                    account_ids.append(party.account_payable.id)
                if party.account_receivable:
                    account_ids.append(party.account_receivable.id)
                party_ids.append(party.id)
        return {
            'all_accounts': not account_ids,
            'accounts': account_ids,
            'all_parties': not party_ids,
            'parties': party_ids,
            }


class GeneralLedgerReport(JasperReport):
    __name__ = 'account_jasper_reports.general_ledger'

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        Period = pool.get('account.period')
        Account = pool.get('account.account')
        Party = pool.get('party.party')
        Line = pool.get('account.move.line')
        fiscalyear = FiscalYear(data['fiscalyear'])
        start_period = None
        if data['start_period']:
            start_period = Period(data['start_period'])
        end_period = None
        if data['end_period']:
            end_period = Period(data['end_period'])
        accounts = Account.browse(data.get('accounts', []))
        parties = Party.browse(data.get('parties', []))
        if accounts:
            js = Account.search([('id', 'in', [x.id for x in accounts])])
            accounts_subtitle = []
            for x in js:
                if len(accounts_subtitle) > 4:
                    accounts_subtitle.append('...')
                    break
                accounts_subtitle.append(x.code)
            accounts_subtitle = ', '.join(accounts_subtitle)
        else:
            accounts_subtitle = ''

        if parties:
            js = Party.search([('id', 'in', [x.id for x in parties])])
            parties_subtitle = []
            for x in js:
                if len(parties_subtitle) > 4:
                    parties_subtitle.append('...')
                    break
                parties_subtitle.append(x.name)
            parties_subtitle = '; '.join(parties_subtitle)
        else:
            parties_subtitle = ''

        parameters = {}
        parameters['start_period'] = start_period and start_period.name or ''
        parameters['end_period'] = end_period and end_period.name or ''
        parameters['fiscal_year'] = fiscalyear.name
        parameters['accounts'] = accounts_subtitle
        parameters['parties'] = parties_subtitle

        domain = []
        if accounts:
            accounts = [('account', 'in', accounts)]
            domain += accounts

        filter_periods = fiscalyear.get_periods(start_period, end_period)
        domain += [('period', 'in', filter_periods)]

        parties_domain = []
        if parties:
            parties_domain = [
                'OR', [
                    ('account.kind', 'not in', ['receivable', 'payable']),
                ], [
                    ('account.kind', 'in', ['receivable', 'payable']),
                    ('party', 'in', parties)]
                ]
            domain += parties_domain

        visible_ids = Line.search(domain)
        line_domain = accounts
        line_domain += parties_domain
        line_domain += [('period', 'in', filter_periods)]
        lines = Line.search(line_domain)
        line_ids = []
        if lines:
            cursor = Transaction().cursor
            cursor.execute("""
                SELECT
                    aml.id
                FROM
                    account_move_line aml,
                    account_move am,
                    account_account aa
                WHERE
                    am.id = aml.move AND
                    aa.id = aml.account AND
                    aml.id in (%s)
                ORDER BY
                    aml.account,
                    -- Sort by party only when account is of
                    -- type 'receivable' or 'payable'
                    CASE WHEN aa.kind in ('receivable', 'payable') THEN
                           aml.party ELSE 0 END,
                    am.date, am.description
                """ % ','.join([str(x.id) for x in lines]))
            line_ids = [x[0] for x in cursor.fetchall()]

        records = []
        lastKey = None
        sequence = 0
        for line in Line.browse(line_ids):
            if line.account.kind in ('receivable', 'payable'):
                currentKey = (line.account, line.party and line.party
                    or None)
            else:
                currentKey = line.account
            if lastKey != currentKey:
                lastKey = currentKey
                balance = Decimal('0.00')
            balance += line.debit - line.credit
            if line in visible_ids:
                sequence += 1
                records.append({
                        'sequence': sequence,
                        'key': str(currentKey),
                        'account_code': line.account.code,
                        'account_name': line.account.name,
                        'account_type': line.account.kind,
                        'date': line.date.strftime('%d/%m/%Y'),
                        'move_line_name': line.description,
                        'ref': line.origin,
                        'move_name': line.move.description,
                        'party_name': line.party and line.party.name or '',
                        'credit': line.credit,
                        'debit': line.debit,
                        'balance': balance,
                        })
        return super(GeneralLedgerReport, cls).execute(ids, {
                'name': 'account_jasper_reports.general_ledger',
                'model': 'account.move.line',
                'data_source': 'records',
                'records': records,
                'parameters': parameters,
                'output_format': data['output_type'],
                })

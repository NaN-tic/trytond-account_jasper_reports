# This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
# at the top level of this repository contains the full copyright notices and
# license terms.
from datetime import timedelta
from decimal import Decimal

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import Eval
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['PrintGeneralLedgerStart', 'PrintGeneralLedger',
    'GeneralLedgerReport']


class PrintGeneralLedgerStart(ModelView):
    'Print General Ledger'
    __name__ = 'account_jasper_reports.print_general_ledger.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    start_period = fields.Many2One('account.period', 'Start Period',
        required=True,
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ], depends=['fiscalyear', 'end_period'])
    end_period = fields.Many2One('account.period', 'End Period',
        required=True,
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['fiscalyear', 'start_period'])
    accounts = fields.Many2Many('account.account', None, None, 'Accounts')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    output_format = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Format', required=True)
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

    @fields.depends('fiscalyear')
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
            'output_format': self.start.output_format,
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
            'accounts': account_ids,
            'parties': party_ids,
            }


class GeneralLedgerReport(JasperReport):
    __name__ = 'account_jasper_reports.general_ledger'

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        Company = pool.get('company.company')
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
        with Transaction().set_context(active_test=False):
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

        company = None
        if data['company']:
            company = Company(data['company'])

        parameters = {}
        parameters['start_period'] = start_period and start_period.name or ''
        parameters['end_period'] = end_period and end_period.name or ''
        parameters['fiscal_year'] = fiscalyear.name
        parameters['accounts'] = accounts_subtitle
        parameters['parties'] = parties_subtitle
        parameters['company_rec_name'] = company and company.rec_name or ''
        parameters['company_vat'] = company and company.party.vat_number or ''

        domain = []
        if accounts:
            domain += [('account', 'in', accounts)]
        else:
            with Transaction().set_context(active_test=False):
                accounts = Account.search([('parent', '!=', None)])

        filter_periods = fiscalyear.get_periods(start_period, end_period)
        domain += [('period', 'in', filter_periods)]

        parties_domain = []
        if parties:
            parties_domain = [
                'OR', [
                    ('account.kind', 'in', ['receivable', 'payable']),
                    ('party', 'in', [p.id for p in parties])],
                [
                    ('account.kind', 'not in', ['receivable', 'payable'])
                ]]
            domain.append(parties_domain)

        lines = Line.search(domain)
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
                    am.date,
                    am.description,
                    aml.id
                """ % ','.join([str(x.id) for x in lines]))
            line_ids = [x[0] for x in cursor.fetchall()]

        initial_balance_date = start_period.start_date - timedelta(days=1)
        with Transaction().set_context(date=initial_balance_date):
            init_values = Account.read_account_vals(accounts, with_moves=True,
                exclude_party_moves=True)
        with Transaction().set_context(date=initial_balance_date):
            init_party_values = Party.get_account_values_by_party(
                parties, accounts)

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
                if isinstance(currentKey, tuple):
                    account_id = currentKey[0].id
                    party_id = currentKey[1].id if currentKey[1] else None
                else:
                    account_id = currentKey.id
                    party_id = None
                if party_id:
                    balance = init_party_values.get(account_id,
                        {}).get(party_id, {}).get('balance', Decimal(0))
                else:
                    balance = init_values.get(account_id, {}).get('balance',
                        Decimal(0))
            balance += line.debit - line.credit
            sequence += 1
            records.append({
                    'sequence': sequence,
                    'key': str(currentKey),
                    'account_code': line.account.code or '',
                    'account_name': line.account.name or '',
                    'account_type': line.account.kind,
                    'date': line.date.strftime('%d/%m/%Y'),
                    'move_line_name': line.description or '',
                    'ref': (line.origin.rec_name if line.origin and
                        hasattr(line.origin, 'rec_name') else ''),
                    'move_number': line.move.number,
                    'move_post_number': (line.move.post_number
                        if line.move.post_number else ''),
                    'party_name': line.party.name if line.party else '',
                    'credit': line.credit,
                    'debit': line.debit,
                    'balance': balance,
                    })
        return records, parameters

    @classmethod
    def execute(cls, ids, data):
        with Transaction().set_context(active_test=False):
            records, parameters = cls.prepare(data)
        return super(GeneralLedgerReport, cls).execute(ids, {
                'name': 'account_jasper_reports.general_ledger',
                'model': 'account.move.line',
                'data_source': 'records',
                'records': records,
                'parameters': parameters,
                'output_format': data['output_format'],
                })

# This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
# at the top level of this repository contains the full copyright notices and
# license terms.
from datetime import timedelta
from decimal import Decimal

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateReport, Button
from trytond.pyson import Eval, Bool, If
from trytond.modules.jasper_reports.jasper import JasperReport
from trytond.tools import grouped_slice


class PrintGeneralLedgerStart(ModelView):
    'Print General Ledger'
    __name__ = 'account_jasper_reports.print_general_ledger.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        states={
            'invisible': Eval('start_date') | Eval('end_date'),
            'required': ~Eval('start_date') & ~Eval('end_date'),
            })
    start_period = fields.Many2One('account.period', 'Start Period',
        states={
            'invisible': Eval('start_date') | Eval('end_date'),
            },
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            If(Bool(Eval('end_period')),
                ('start_date', '<=', (Eval('end_period'), 'start_date')),
                (),
                ),
            ], depends=['fiscalyear', 'end_period'])
    end_period = fields.Many2One('account.period', 'End Period',
        states={
            'invisible': Eval('start_date') | Eval('end_date'),
            },
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            If(Bool(Eval('start_period')),
                ('start_date', '>=', (Eval('start_period'), 'start_date')),
                (),
                ),
            ],
        depends=['fiscalyear', 'start_period'])
    start_date = fields.Date('Initial posting date',
        domain=[
            If(Eval('start_date') & Eval('end_date'),
                ('start_date', '<=', Eval('end_date', None)),
                ()),
            ],
        states={
            'invisible': Eval('start_period') | Eval('end_period'),
            'required': ((Eval('start_date') | Eval('end_date')) &
                ~Bool(Eval('start_period') | Eval('end_period'))),
            },
        depends=['end_date'])
    end_date = fields.Date('Final posting date',
        domain=[
            If(Eval('start_date') & Eval('end_date'),
                ('end_date', '>=', Eval('start_date', None)),
                ()),
            ],
        states={
            'invisible': Eval('start_period') | Eval('end_period'),
            'required': ((Eval('end_date') | Eval('start_date')) &
                ~Bool(Eval('start_period') | Eval('end_period')))
            },
        depends=['start_date'])
    accounts = fields.Many2Many('account.account', None, None, 'Accounts')
    all_accounts = fields.Boolean('All accounts with and without balance',
        help='If unchecked only print accounts with previous balance different'
        ' from 0 or with moves')
    parties = fields.Many2Many('party.party', None, None, 'Parties', 
        context={
            'company': Eval('company'),
            },
        depends=['company'])
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
    def default_all_accounts():
        return True

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_output_format():
        return 'pdf'

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        self.start_period = None
        self.end_period = None


class PrintGeneralLedger(Wizard):
    'Print GeneralLedger'
    __name__ = 'account_jasper_reports.print_general_ledger'
    start = StateView('account_jasper_reports.print_general_ledger.start',
        'account_jasper_reports.print_general_ledger_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateReport('account_jasper_reports.general_ledger')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear': (self.start.fiscalyear.id if self.start.fiscalyear
                else None),
            'start_period': (self.start.start_period.id
                if self.start.start_period else None),
            'end_period': (self.start.end_period.id if self.start.end_period
                else None),
            'start_date': self.start.start_date,
            'end_date': self.start.end_date,
            'accounts': [x.id for x in self.start.accounts],
            'all_accounts': self.start.all_accounts,
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

        fiscalyear = (FiscalYear(data['fiscalyear']) if data.get('fiscalyear')
            else None)
        start_period = (Period(data['start_period']) if data.get(
                'start_period') else None)
        end_period = (Period(data['end_period']) if data.get('end_period')
            else None)
        start_date = data['start_date'] if data.get('start_date') else None
        end_date = data['end_date'] if data .get('end_date') else None
        with Transaction().set_context(active_test=False):
            accounts = Account.browse(data.get('accounts', []))
            parties = Party.browse(data.get('parties', []))
            if accounts:
                accounts_subtitle = []
                for x in accounts:
                    if len(accounts_subtitle) > 4:
                        accounts_subtitle.append('...')
                        break
                    accounts_subtitle.append(x.code)
                accounts_subtitle = ', '.join(accounts_subtitle)
            else:
                accounts_subtitle = ''

            if parties:
                parties_subtitle = []
                for x in parties:
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
        parameters['company'] = (company.rec_name if company else
            fiscalyear.company.res_name)
        parameters['start_period'] = start_period and start_period.name or ''
        parameters['end_period'] = end_period and end_period.name or ''
        parameters['start_date'] = (start_date.strftime('%d/%m/%Y')
            if start_date else '')
        parameters['end_date'] = (end_date.strftime('%d/%m/%Y')
            if end_date else '')
        parameters['fiscal_year'] = fiscalyear.rec_name if fiscalyear else ''
        parameters['accounts'] = accounts_subtitle
        parameters['parties'] = parties_subtitle
        parameters['company_rec_name'] = company and company.rec_name or ''
        parameters['company_vat'] = (company
            and company.party.tax_identifier and
            company.party.tax_identifier.code) or ''

        where = ''
        if accounts:
            where += "aml.account in (%s) " % (
                ",".join([str(a.id) for a in accounts]))
        else:
            where += "aa.parent is not null "

        if start_date:
            if company:
                where += "and am.company = %s " % company.id
            where += "and am.date >= '%s' " % start_date
            where += "and am.date <= '%s' " % end_date
        else:
            filter_periods = fiscalyear.get_periods(start_period, end_period)
            where += "and am.period in (%s) " % (
                ",".join([str(a.id) for a in filter_periods]))

        if parties:
            where += " and aml.party in (%s)" % (
                ",".join([str(a.id) for a in parties]))

        cursor = Transaction().connection.cursor()
        cursor.execute("""
            SELECT
                aml.id
            FROM
                account_move_line aml,
                account_move am,
                account_account aa,
                account_account_type aat
            WHERE
                am.id = aml.move AND
                aa.id = aml.account AND
                aa.type = aat.id AND
                %s
            ORDER BY
                aml.account,
                -- Sort by party only when account is of
                -- type 'receivable' or 'payable'
                -- or party_requierd is True
                CASE WHEN aat.receivable or aat.payable or
                    aa.party_required THEN aml.party ELSE 0 END,
                am.date,
                am.id,
                am.description,
                aml.id
            """ % where)
        line_ids = [x[0] for x in cursor.fetchall()]

        if not start_date:
            start_date = (start_period.start_date if start_period else
                fiscalyear.start_date)
        initial_balance_date = start_date - timedelta(days=1)
        with Transaction().set_context(date=initial_balance_date):
            init_values = {}
            if not parties:
                init_values = Account.read_account_vals(accounts,
                    with_moves=False, exclude_party_moves=True)
            init_party_values = Party.get_account_values_by_party(
                parties, accounts, (company or fiscalyear.company))

        records = []
        parties_general_ledger = set()
        lastKey = None
        sequence = 0
        accounts_w_moves = []
        for group_lines in grouped_slice(line_ids):
            for line in Line.browse(group_lines):
                if line.account not in accounts_w_moves:
                    accounts_w_moves.append(line.account.id)
                if ((line.account.type.receivable is True or
                            line.account.type.payable is True or
                            line.account.party_required) and line.party):
                    currentKey = (line.account, line.party)
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
                        parties_general_ledger.add(party_id)
                        balance = init_party_values.get(account_id,
                            {}).get(party_id, {}).get('balance', Decimal(0))
                    else:
                        balance = init_values.get(account_id, {}).get(
                            'balance', Decimal(0))
                balance += line.debit - line.credit
                sequence += 1
                account_type = 'other'
                if line.account.type and line.account.type.receivable:
                    account_type = 'receivable'
                elif line.account.type and line.account.type.payable:
                    account_type = 'payable'
                records.append({
                        'sequence': sequence,
                        'key': str(currentKey),
                        'account_code': line.account.code or '',
                        'account_name': line.account.name or '',
                        'account_type': account_type,
                        'account_party_required': line.account.party_required,
                        'date': line.date.strftime('%d/%m/%Y'),
                        'move_line_name': line.description or '',
                        'ref': (line.move_origin.rec_name
                            if line.move_origin and
                            hasattr(line.move_origin, 'rec_name') else ''),
                        'party_origin': (line.move_origin.party.rec_name
                            if line.move_origin
                            and hasattr(line.move_origin, 'party') else ''),
                        'move_number': line.move.number,
                        'move_post_number': (line.move.post_number
                            if line.move.post_number else ''),
                        'party_name': line.party.name if line.party else '',
                        'credit': line.credit,
                        'debit': line.debit,
                        'balance': balance,
                        })

        if data.get('all_accounts', True):
            init_values_account_wo_moves = {
                k: init_values[k] for k in init_values
                if k not in accounts_w_moves}
            for account_id, values in init_values_account_wo_moves.items():
                account = Account(account_id)
                balance = values.get('balance', Decimal(0))
                credit = values.get('credit', Decimal(0))
                debit = values.get('debit', Decimal(0))
                if balance == 0:
                    continue
                account_type = 'other'
                if account.type and account.type.receivable:
                    account_type = 'receivable'
                elif account.type and account.type.payable:
                    account_type = 'payable'
                records.append({
                        'sequence': 1,
                        'key': str(account),
                        'account_code': account.code or '',
                        'account_name': account.name or '',
                        'account_type': account_type,
                        'move_line_name': '###PREVIOUSBALANCE###',
                        'ref': '-',
                        'move_number': '-',
                        'move_post_number': '-',
                        'credit': credit,
                        'debit': debit,
                        'balance': balance,
                        })

            if parties or parties_general_ledger:
                account_ids = [k for k, _ in init_party_values.items()]
                accounts = dict((a.id, a) for a in Account.browse(account_ids))
                if parties:
                    parties = dict((p.id, p) for p in parties)
                elif parties_general_ledger:
                    parties = dict((p, Party(p))
                        for a, av in init_party_values.items()
                        for p, pv in av.items()
                        if p and p not in parties_general_ledger)

                if parties:
                    for k, v in init_party_values.items():
                        account = accounts[k]
                        for p, z in v.items():
                            # check if party is in current general ledger
                            if not p or p in parties_general_ledger:
                                continue
                            party = parties[p]
                            if (account.type.receivable or account.type.payable
                                    or account.party_required):
                                currentKey = (account, party)
                            else:
                                currentKey = account
                            sequence += 1
                            balance = z.get('balance', Decimal(0))
                            if balance:
                                account_type = 'other'
                                if account.type and account.type.receivable:
                                    account_type = 'receivable'
                                elif account.type and account.type.payable:
                                    account_type = 'payable'
                                records.append({
                                        'sequence': sequence,
                                        'key': str(currentKey),
                                        'account_code': account.code or '',
                                        'account_name': account.name or '',
                                        'account_type': account_type,
                                        'account_party_required': (
                                            account.party_required),
                                        'move_line_name': (
                                            '###PREVIOUSBALANCE###'),
                                        'ref': '-',
                                        'move_number': '-',
                                        'move_post_number': '-',
                                        'party_name': party.name,
                                        'credit': z.get('credit', Decimal(0)),
                                        'debit': z.get('debit', Decimal(0)),
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

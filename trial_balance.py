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

__all__ = ['PrintTrialBalanceStart', 'PrintTrialBalance',
    'TrialBalanceReport']


class PrintTrialBalanceStart(ModelView):
    'Print Trial Balance Start'
    __name__ = 'account_jasper_reports.print_trial_balance.start'

    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True, on_change=['fiscalyear'])
    comparison_fiscalyear = fields.Many2One('account.fiscalyear',
            'Fiscal Year', on_change=['comparison_fiscalyear'])
    show_digits = fields.Integer('Digits')
    with_move_only = fields.Boolean('Only Accounts With Move')
    accounts = fields.Many2Many('account.account', None, None, 'Accounts')
    split_parties = fields.Boolean('Split Parties')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ],
        states={
            'required': Bool(Eval('fiscalyear'))
        },
        depends=['fiscalyear', 'end_period']
        )
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        states={
            'required': Bool(Eval('fiscalyear'))
        },
        depends=['fiscalyear', 'start_period'])

    comparison_start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('comparison_fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ],
        states={
            'required': Bool(Eval('comparison_fiscalyear'))
        }, depends=['comparison_fiscalyear', 'end_period'])

    comparison_end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('comparison_fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        states={
            'required': Bool(Eval('comparison_fiscalyear'))
        },
        depends=['comparison_fiscalyear', 'start_period'])
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
    def default_output_type():
        return 'pdf'

    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }

    def on_change_comparison_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }


class PrintTrialBalance(Wizard):
    'Print TrialBalance'
    __name__ = 'account_jasper_reports.print_trial_balance'
    start = StateView('account_jasper_reports.print_trial_balance.start',
        'account_jasper_reports.print_trial_balance_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('account_jasper_reports.report_trial_balance')

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
            'comparison_fiscalyear': self.start.comparison_fiscalyear and
                self.start.comparison_fiscalyear.id or None,
            'start_period': start_period,
            'end_period': end_period,
            'comparison_start_period': self.start.comparison_start_period and
                self.start.comparison_start_period.id or None,
            'comparison_end_period': self.start.comparison_end_period and
                self.start.comparison_end_period.id or None,
            'digits': self.start.show_digits or None,
            'with_move_only': self.start.with_move_only,
            'split_parties': self.start.split_parties,
            'accounts': [x.id for x in self.start.accounts],
            'parties': [x.id for x in self.start.parties],
            'output_type': self.start.output_type,
            }

        print "a:", data
        print "action:", action
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


class TrialBalanceReport(JasperReport):
    __name__ = 'account_jasper_reports.trial_balance'

    @classmethod
    def read_account_vals(cls, accounts):
        pool = Pool()
        Account = pool.get('account.account')
        offset = 3000
        index = 0
        values = {}
        while index * offset < len(accounts):
            chunk = [x.id for x in
                accounts[index * offset: (index + 1) * offset]]
            index += 1
            for x in Account.read(chunk, ['credit', 'debit', 'balance']):
                values[x['id']] = {
                    'credit': x['credit'],
                    'debit': x['debit'],
                    'balance': x['balance'],
                    }
        return values

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        Period = pool.get('account.period')
        Account = pool.get('account.account')
        Party = pool.get('party.party')

        print "data:", data
        fiscalyear = FiscalYear(data['fiscalyear'])
        comparison_fiscalyear = None
        if data['comparison_fiscalyear']:
            comparison_fiscalyear = FiscalYear(data['comparison_fiscalyear'])

        start_period = None
        if data['start_period']:
            start_period = Period(data['start_period'])
        end_period = None
        if data['end_period']:
            end_period = Period(data['end_period'])
        comparison_start_period = None
        if data['comparison_start_period']:
            comparison_start_period = Period(data['comparison_start_period'])
        comparison_end_period = None
        if data['comparison_end_period']:
            comparison_end_period = Period(data['comparison_end_period'])

        split_parties = data['split_parties']
        accounts = data['accounts']
        parties = data['parties']
        digits = data['digits']
        with_moves_only = data['with_move_only']

        periods = fiscalyear.get_periods(start_period, end_period)
        if comparison_fiscalyear:
            comparison_periods = comparison_fiscalyear.get_periods(
                comparison_start_period, comparison_end_period)

        domain = []
        if accounts:
            accounts = [('account', 'in', accounts)]
            domain += accounts

        domain += [('period', 'in', periods)]

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

        accounts.append(('parent', '!=', None))
        accounts = Account.search(accounts, order=[('code', 'ASC')])
        #TODO:: constraint, start period cannot be period of pyg or close
        #if first_period.special and first_period.date_start[8:10] != '01':
            ## It's a 'Closing period'
            #raise osv.except_osv(
                    #_("Periods Selection Warning!"),
                    #_("The Trial Balance report is not supported for "
                      #"selection of periods starting with a "
                      #"'Closing Period'."))
        #if not start_period.special:

        # Calc first period values
        #first_dict = {}.fromkeys(accounts, Decimal('0.00'))
        with Transaction().set_context(fiscalyear=fiscalyear.id,
                date=None, periods=periods):
            values = cls.read_account_vals(accounts)

        # Calc Initial Balance for first period
        initial_periods = Period.search([
                ('fiscalyear', '=', fiscalyear.id),
                ('start_date', '<=', start_period.start_date),
                ('end_date', '<', start_period.end_date),
            ])

        with Transaction().set_context(fiscalyear=fiscalyear.id,
                date=None, periods=initial_periods):
            init_values = cls.read_account_vals(accounts)

        # Calc comparison period values.
        comparison_initial_values = {}.fromkeys(accounts, Decimal('0.00'))
        comparison_values = {}.fromkeys(accounts, Decimal('0.00'))

        if comparison_fiscalyear:
        #    second_dict = {}.fromkeys(accounts, Decimal('0.00'))
            with Transaction().set_context(fiscalyear=comparison_fiscalyear.id,
                    date=None, periods=comparison_periods):
                comparison_values = cls.read_account_vals(accounts)

            # Calc Initial Balance for comparison period
            initial_comparison_periods = Period.search([
                    ('fiscalyear', '=', comparison_fiscalyear.id),
                    ('start_date', '<=', comparison_start_period.start_date),
                    ('end_date', '<', comparison_end_period.end_date),
                ])

            with Transaction().set_context(fiscalyear=fiscalyear.id,
                    date=None, periods=initial_comparison_periods):
                comparison_initial_values.update(
                    cls.read_account_vals(accounts))

        init_partners_values = {}
        partner_values = {}
        init_comparision_partner_values = {}
        comparison_partner_values = {}

        if split_parties:
            if not parties:
                parties = Party.search([])

            with Transaction().set_context(fiscalyear=fiscalyear.id,
                    date=None, periods=initial_periods):
                init_party_values = cls.get_account_values_by_party(
                    parties, accounts)

            with Transaction().set_context(fiscalyear=fiscalyear.id,
                    date=None, periods=periods):
                party_values = cls.get_account_values_by_party(
                    parties, accounts)

            if comparison_fiscalyear:
                with Transaction().set_context(fiscalyear=fiscalyear.id,
                        date=None, periods=initial_comparison_periods):
                    init_comparison_party_values = \
                        cls.get_account_values_by_party(parties, accounts)

                with Transaction().set_context(fiscalyear=fiscalyear.id,
                        date=None, periods=comparison_periods):
                    comparison_party_values = \
                        cls.get_account_values_by_party(parties, accounts)

        records = []
        if digits is None:
            offset = 3000
            index = 0
            while index * offset < len(accounts):
                chunk = accounts[index * offset: (index + 1) * offset]
                index += 1
                for account in chunk:
                    print account
                    initial_balance = init_values[account.id]['balance']
                    credit = values[account.id]['credit']
                    debit = values[account.id]['debit']
                    balance = values[account.id]['balance']

                    # Only print accounts that have moves or initial balance
                    if with_moves_only and not debit and not credit and \
                            not initial_balance:
                        continue

                    comparison_initial_balance = \
                        comparison_initial_values.get(account.id) and \
                        comparison_initial_values[account.id]['balance'] or \
                        Decimal('0.00')
                    comparison_credit = comparison_values.get(account.id) and\
                        comparison_values[account.id]['credit'] or \
                        Decimal('0.00')
                    comparison_debit = comparison_values.get(account.id) and\
                        comparison_values[account.id]['debit'] or \
                        Decimal('0.00')
                    comparison_balance = comparison_values.get(account.id) and\
                        comparison_values[account.id]['balance'] or\
                        Decimal('0.00')

                    if split_parties and parties and \
                            account.type in ['payable', 'receivable']:
                        for party in parties:
                            period_initial_balance = init_party_values.get(
                                account.id, {}).get(party.id, {}).get(
                                'balance', Decimal('0.00'))
                            period_vals = party_values.get(account.id, {}
                                ).get(party.id, {})
                            period_credit = period_vals.get('credit',
                                Decimal('0.00'))
                            period_debit = period_vals.get('debit',
                                Decimal('0.00'))
                            period_balance = period_initial_balance + \
                                period_vlas.get('balance', Decimal('0.00'))

                            if with_moves_only and not period_debit and not\
                               period_credit and not period_initial_balance:
                                continue

                            comp_initial_balance = \
                                init_comparison_party_values.get(
                                    account.id, {}).get(party.id, {}).get(
                                    'balance', Decimal('0.00'))
                            comp_period_vals = comparison_party_values.get(
                                account.id, {}).get(party.id, {})
                            comp_period_credit = comparison_party_vals.get(
                                'credit' ,Decimal('0.00'))
                            comp_period_debit = comparison_period_vals.get(
                                'debit', Decimal('0.00'))

                            comp_period_balance = com_initial_balance + \
                                comparison_period_vals.get('balance',
                                    Decimal('0.00'))

                            record = {
                                'code': account.code,
                                'name': partner.name,
                                'type': account.type, # Useful for the report designer so accounts of type 'view' may be discarded in aggregation.
#                                'second_balance': second_balance,
                                'period_initial_balance': period_initial_balance,
                                'period_credit': period_credit,
                                'period_debit': period_debit,
                                'period_balance': period_balance,
                                'initial_balance': comp_initial_balance,
                                'credit': comp_period_credit,
                                'debit': comp_period_debit,
                                'balance': comp_balance,
                                }
                            records.append(record)
                    else:
                        period_balance = initial_balance + balance
                        comp_period_balance = comparison_initial_balance + \
                                comparison_balance
                        record = {
                            'code': account.code,
                            'name': account.name,
                            'type': account.type, # Useful for the report designer so accounts of type 'view' may be discarded in aggregation.
#                            'second_balance': second_balance,
                            'period_initial_balance': initial_balance,
                            'period_credit': credit,
                            'period_debit': debit,
                            'period_balance': period_balance,
#                           'period_add_initial_balance': add_initial_balance,
                            'initial_balance': comparison_initial_balance,
                            'credit': comparison_credit,
                            'debit': comparison_debit,
                            'balance': comp_period_balance,
                            'second_balance': False if comparison_fiscalyear \
                                    is None else True
#                            'add_initial_balance': comparison_add_initial_balance,
                            }
                        records.append(record)
        else: #LIMIT DIGITS!
            virt_records ={}
            ok_records =[]
            offset = 3000
            index = 0
            while index * offset < len(accountIds):
                chunk = accountIds[index * offset: (index+1) * offset]
                index += 1
                for account in pool.get('account.account').browse(cr, uid, chunk, periodContext):
                    initial_balance = initial_balance_dict[account.id]
                    # Only print accounts that have moves or initial balance and avoid codes with less digits
                    if (with_moves_only and not account.debit and not account.credit and not initial_balance)\
                            or len(account.code.strip()) < digits:
                        continue
                    comparison_values = comparison_dict.get(account.id)
                    comparison_initial_balance = comparison_initial_balance_dict.get(account.id, 0)
                    if len(account.code.strip()) == digits:
                        if split_partners and partners and account.type in ['payable','receivable']:
                            for partner in pool.get('res.partner').browse(cr, uid, partners, context):
                                period_initial_balance = accountPartnersInitial\
                                        .get(account.id, {}).get(partner.id, {})\
                                        .get('balance', 0)
                                period_credit = accountPartners.get(account.id, {}).get(partner.id, {}).get('credit', 0)
                                period_debit = accountPartners.get(account.id, {}).get(partner.id, {}).get('debit', 0)
                                if with_moves_only and not period_debit and not period_credit and not period_initial_balance:
                                    continue
                                comp_initial_balance = accountPartnersCompInitial\
                                        .get(account.id, {}).get(partner.id, {})\
                                        .get('balance', 0)
                                period_balance = (add_initial_balance and period_initial_balance or 0) +\
                                            (accountPartners.get(account.id, {})\
                                                    .get(partner.id, {})\
                                                    .get('balance', 0))
                                comp_balance = (comparison_add_initial_balance and comp_initial_balance or 0) +\
                                            (accountPartnersComparison.get(account.id, {})\
                                            .get(partner.id, {}).get('balance', 0))
                                record = {
                                    'code': account.code,
                                    'name': partner.name,
                                    'type': 'fix', # Useful for the report designer so accounts of type 'view' may be discarded in aggregation.
                                    'second_balance': second_balance,
                                    'period_initial_balance': period_initial_balance,
                                    'period_credit': period_credit,
                                    'period_debit': period_debit,
                                    'period_balance': period_balance,
                                    'period_add_initial_balance': add_initial_balance,
                                    'initial_balance': comp_initial_balance,
                                    'credit': accountPartnersComparison.get(account.id, {}).get(partner.id, {}).get('credit', 0),
                                    'debit': accountPartnersComparison.get(account.id, {}).get(partner.id, {}).get('debit', 0),
                                    'balance': comp_balance,
                                    'add_initial_balance': comparison_add_initial_balance,
                                }
                                ok_records.append(account.code)
                                records.append(record)
                        else:
                            period_balance = (add_initial_balance and initial_balance or 0) + account.balance
                            comp_balance = comparison_values and\
                                    ((comparison_add_initial_balance and comparison_initial_balance or 0) +\
                                    comparison_values['balance']) or 0
                            record = {
                                'code': account.code,
                                'name': account.name,
                                'type': 'fix', # Useful for the report designer so accounts of type 'view' may be discarded in aggregation.
                                'second_balance': second_balance,
                                'period_initial_balance': initial_balance,
                                'period_credit': account.credit,
                                'period_debit': account.debit,
                                'period_balance': period_balance,
                                'period_add_initial_balance': add_initial_balance,
                                'initial_balance': comparison_initial_balance,
                                'credit': comparison_values and comparison_values['credit'] or 0,
                                'debit': comparison_values and comparison_values['debit'] or 0,
                                'balance': comp_balance,
                                'add_initial_balance': comparison_add_initial_balance,
                            }
                            ok_records.append(account.code)
                            records.append(record)
                    else:
                        virt_code = account.code[:digits]
                        # We can make this comparation because records are
                        # sorted by code. Account with larger codes comes later
                        # than shorter
                        if virt_code in ok_records:
                            continue
                        record = virt_records.get(virt_code)
                        initial_balance += virt_records.get(virt_code, {}).get('period_initial_balance',0)
                        comparison_initial_balance += virt_records.get( virt_code, {} ).get('initial_balance',0)
                        period_balance = (add_initial_balance and initial_balance or 0) +\
                                account.balance +\
                                virt_records.get(virt_code, {}).get('period_balance',0)
                        comp_balance = comparison_values and\
                                ((comparison_add_initial_balance and comparison_initial_balance or 0) +\
                                comparison_values['balance'] + virt_records.get(virt_code, {}).get('balance',0)) or 0
                        record = {
                                'code': virt_code,
                                'name': " ",
                                'type': 'fix', # Useful for the report designer so accounts of type 'view' may be discarded in aggregation.
                                'second_balance': second_balance,
                                'period_initial_balance': initial_balance,
                                'period_credit': account.credit  + virt_records.get( virt_code, {} ).get('period_credit',0),
                                'period_debit': account.debit + virt_records.get( virt_code, {} ).get('period_debit',0),
                                'period_balance': period_balance,
                                'period_add_initial_balance': add_initial_balance,
                                'initial_balance': comparison_initial_balance,
                                'credit': comparison_values and comparison_values['credit'] + virt_records.get( virt_code, {} ).get('credit',0) or 0,
                                'debit': comparison_values and comparison_values['debit'] + virt_records.get( virt_code, {} ).get('debit',0) or 0,
                                'balance': comp_balance,
                                'add_initial_balance': comparison_add_initial_balance,
                        }
                        virt_records[virt_code] = record

            for record in virt_records:
                records.append( virt_records[record] )

        parameters=[]
        return super(TrialBalanceReport, cls).execute(ids, {
                'name': 'account_jasper_reports.trial_balance',
                'model': 'account.move.line',
                'data_source': 'records',
                'records': records,
                'parameters': parameters,
                'output_format': data['output_type'],

            })




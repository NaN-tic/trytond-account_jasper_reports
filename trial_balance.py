# The COPYRIGHT filei at the top level of this repository contains the full
# copyright notices and License terms.
from datetime import timedelta
from decimal import Decimal
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateReport, Button
from trytond.pyson import Eval, Bool, If
from trytond.modules.jasper_reports.jasper import JasperReport
import logging

__all__ = ['PrintTrialBalanceStart', 'PrintTrialBalance',
    'TrialBalanceReport']

_ZERO = Decimal('0.00')
logger = logging.getLogger(__name__)


class PrintTrialBalanceStart(ModelView):
    'Print Trial Balance Start'
    __name__ = 'account_jasper_reports.print_trial_balance.start'

    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    comparison_fiscalyear = fields.Many2One('account.fiscalyear',
            'Fiscal Year')
    show_digits = fields.Integer('Digits')
    with_move_only = fields.Boolean('Only Accounts With Move',
        states={
            'invisible': Bool(Eval('add_initial_balance') &
                Eval('with_move_or_initial'))
        },
        depends=['with_move_or_initial'])
    with_move_or_initial = fields.Boolean(
        'Only Accounts With Moves or Initial Balance',
        states={
            'invisible': ~Bool(Eval('add_initial_balance'))
        },
        depends=['add_initial_balance'])
    accounts = fields.Many2Many('account.account', None, None, 'Accounts')
    split_parties = fields.Boolean('Split Parties')
    add_initial_balance = fields.Boolean('Add Initial Balance')
    parties = fields.Many2Many('party.party', None, None, 'Parties',
        states={
            'invisible': ~Bool(Eval('split_parties', False)),
            },
        depends=['split_parties'])
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            If(Bool(Eval('end_period')),
                ('start_date', '<=', (Eval('end_period'), 'start_date')),
                (),
                ),
            ],
        depends=['fiscalyear', 'end_period']
        )
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            If(Bool(Eval('start_period')),
                ('start_date', '>=', (Eval('start_period'), 'start_date')),
                (),
                )
            ],
        depends=['fiscalyear', 'start_period'])

    comparison_start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('comparison_fiscalyear')),
            ('start_date', '<=', (Eval('comparison_end_period'),
                    'start_date')),
            ],
        depends=['comparison_fiscalyear', 'comparison_end_period'])
    comparison_end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('comparison_fiscalyear')),
            ('start_date', '>=', (Eval('comparison_start_period'),
                    'start_date'))
            ],
        depends=['comparison_fiscalyear', 'comparison_start_period'])
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
    def default_start_period():
        FiscalYear = Pool().get('account.fiscalyear')
        Period = Pool().get('account.period')
        fiscalyear = FiscalYear.find(
            Transaction().context.get('company'), exception=False)
        clause = [
            ('fiscalyear', '=', fiscalyear),
            ]
        periods = Period.search(clause, order=[('start_date', 'ASC')],
            limit=1)
        if periods:
            return periods[0].id

    @staticmethod
    def default_end_period():
        FiscalYear = Pool().get('account.fiscalyear')
        Period = Pool().get('account.period')
        fiscalyear = FiscalYear.find(
            Transaction().context.get('company'), exception=False)

        Date = Pool().get('ir.date')
        date = Date.today()

        clause = [
            ('fiscalyear', '=', fiscalyear),
            ('start_date', '<=', date),
            ('end_date', '>=', date),
            ]
        periods = Period.search(clause, order=[('start_date', 'ASC')],
            limit=1)
        if periods:
            return periods[0].id

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

    @fields.depends('comparison_fiscalyear')
    def on_change_comparison_fiscalyear(self):
        self.comparison_start_period = None
        self.comparison_end_period = None

    @classmethod
    def view_attributes(cls):
        return [('/form//label[@id="all_parties"]', 'states',
                {'invisible': ~Bool(Eval('split_parties'))})]


class PrintTrialBalance(Wizard):
    'Print TrialBalance'
    __name__ = 'account_jasper_reports.print_trial_balance'
    start = StateView('account_jasper_reports.print_trial_balance.start',
        'account_jasper_reports.print_trial_balance_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateReport('account_jasper_reports.trial_balance')

    def do_print_(self, action):
        start_period = self.start.fiscalyear.periods[0].id
        if self.start.start_period:
            start_period = self.start.start_period.id
        end_period = self.start.fiscalyear.periods[-1].id
        if self.start.end_period:
            end_period = self.start.end_period.id
        comparison_start_period = None
        if self.start.comparison_start_period:
            comparison_start_period = self.start.comparison_start_period.id
        elif (self.start.comparison_fiscalyear
                and self.start.comparison_fiscalyear.periods):
            comparison_start_period = (
                self.start.comparison_fiscalyear.periods[0].id)
        comparison_end_period = None
        if self.start.comparison_end_period:
            comparison_end_period = self.start.comparison_end_period.id
        elif (self.start.comparison_fiscalyear
                and self.start.comparison_fiscalyear.periods):
            comparison_end_period = (
                self.start.comparison_fiscalyear.periods[-1].id)
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'comparison_fiscalyear': (self.start.comparison_fiscalyear and
                self.start.comparison_fiscalyear.id or None),
            'start_period': start_period,
            'end_period': end_period,
            'comparison_start_period': comparison_start_period,
            'comparison_end_period': comparison_end_period,
            'digits': self.start.show_digits or None,
            'add_initial_balance': self.start.add_initial_balance,
            'with_move_only': self.start.with_move_only,
            'with_move_or_initial': self.start.with_move_or_initial,
            'split_parties': self.start.split_parties,
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


class TrialBalanceReport(JasperReport):
    __name__ = 'account_jasper_reports.trial_balance'

    @classmethod
    def prepare(cls, data):
        def _amounts(account, init_vals, vals):
            initial = init_vals.get(account.id, {}).get('balance') or _ZERO
            credit = vals.get(account.id, {}).get('credit') or _ZERO
            debit = vals.get(account.id, {}).get('debit') or _ZERO
            balance = vals.get(account.id, {}).get('balance') or _ZERO
            return initial, credit, debit, balance

        def _party_amounts(account, party_id, init_vals, vals):
            iac_vals = init_vals.get(account.id, {})
            ac_vals = vals.get(account.id, {})
            initial = iac_vals.get(party_id, {}).get('balance') or _ZERO
            credit = ac_vals.get(party_id, {}).get('credit') or _ZERO
            debit = ac_vals.get(party_id, {}).get('debit') or _ZERO
            balance = ac_vals.get(party_id, {}).get('balance') or _ZERO
            return initial, credit, debit, balance

        def _record(account, party, vals, comp, add_initial_balance):
            init, credit, debit, balance = vals
            init_comp, credit_comp, debit_comp, balance_comp = comp
            if add_initial_balance:
                balance += init
                balance_comp += init_comp
            account_type = 'other'
            if account.type and account.type.receivable:
                account_type = 'receivable'
            elif account.type and account.type.payable:
                account_type = 'payable'
            return {
                'code': account.code or '',
                'name': party and party.name or account.name,
                'type': account_type,
                'period_initial_balance': init,
                'period_credit': credit,
                'period_debit': debit,
                'period_balance': balance,
                'initial_balance': init_comp,
                'credit': credit_comp,
                'debit': debit_comp,
                'balance': balance_comp,
            }

        pool = Pool()
        Company = pool.get('company.company')
        FiscalYear = pool.get('account.fiscalyear')
        Period = pool.get('account.period')
        Account = pool.get('account.account')
        Party = pool.get('party.party')
        transaction = Transaction()

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

        company = None
        if data['company']:
            company = Company(data['company'])

        accounts = data['accounts']
        parties = data['parties']
        if parties:
            split_parties = True
        else:
            split_parties = data['split_parties']
        digits = data['digits']
        add_initial_balance = data['add_initial_balance']
        with_moves = data['with_move_only']
        with_moves_or_initial = data['with_move_or_initial']
        if not add_initial_balance:
            with_moves_or_initial = False
        if with_moves_or_initial:
            with_moves = True

        periods = [x.id for x in fiscalyear.get_periods(start_period,
                end_period)]
        if comparison_fiscalyear:
            comparison_periods = [x.id for x in
                comparison_fiscalyear.get_periods(comparison_start_period,
                    comparison_end_period)]

        domain = [('parent', '!=', None)]
        accounts_title = False
        if accounts:
            accounts_title = True
            domain += [('id', 'in', accounts)]

        parameters = {}
        parameters['company'] = fiscalyear.company.rec_name
        parameters['SECOND_BALANCE'] = comparison_fiscalyear and True or False
        parameters['fiscalyear'] = fiscalyear.name
        parameters['comparison_fiscalyear'] = comparison_fiscalyear and \
            comparison_fiscalyear.name or ''
        parameters['start_period'] = start_period and start_period.name or ''
        parameters['end_period'] = end_period and end_period.name or ''
        parameters['comparison_start_period'] = comparison_start_period and\
            comparison_start_period.name or ''
        parameters['comparison_end_period'] = comparison_end_period and\
            comparison_end_period.name or ''
        parameters['company_rec_name'] = company and company.rec_name or ''
        parameters['company_vat'] = (company
            and company.party.tax_identifier and
            company.party.tax_identifier.code) or ''
        parameters['digits'] = digits or ''
        parameters['with_moves_only'] = with_moves or ''
        parameters['split_parties'] = split_parties or ''

        with Transaction().set_context(active_test=False):
            if parties:
                parties = Party.browse(parties)
                parties_subtitle = []
                for x in parties:
                    if len(parties_subtitle) > 4:
                        parties_subtitle.append('...')
                        break
                    parties_subtitle.append(x.name)
                parties_subtitle = '; '.join(parties_subtitle)
            else:
                parties_subtitle = ''

            parameters['parties'] = parties_subtitle
            logger.info('Search accounts')
            accounts = []
            for account in Account.search(domain, order=[('code', 'ASC')]):
                if not account.code:
                    if not digits:
                        accounts.append(account)
                elif not digits or len(account.code) == digits or \
                    account.type != None and len(account.childs) == 0 and \
                        len(account.code) < (digits or 9999):
                    accounts.append(account)

        if accounts_title:
            accounts_subtitle = []
            for x in accounts:
                if len(accounts_subtitle) > 4:
                    accounts_subtitle.append('...')
                    break
                accounts_subtitle.append(x.code)
            accounts_subtitle = ', '.join(accounts_subtitle)
        else:
            accounts_subtitle = ''
        parameters['accounts'] = accounts_subtitle

        logger.info('Calc amounts')
        # Calc first period values
        with transaction.set_context(fiscalyear=fiscalyear.id,
                periods=periods):
            values = Account.read_account_vals(accounts, with_moves=with_moves)

        # Calc Initial Balance for first period
        init_values = {}
        logger.info('Calc Initial Balance')
        initial_balance_date = start_period.start_date - timedelta(days=1)
        with transaction.set_context(date=initial_balance_date):
            init_values = Account.read_account_vals(accounts,
                with_moves=with_moves)

        # Calc comparison period values.
        comparison_initial_values = {}.fromkeys(accounts, Decimal('0.00'))
        comparison_values = {}.fromkeys(accounts, Decimal('0.00'))

        if comparison_fiscalyear:
            # second_dict = {}.fromkeys(accounts, Decimal('0.00'))
            logger.info('Calc initial vals for comparison period')
            with transaction.set_context(periods=comparison_periods):
                comparison_values = Account.read_account_vals(accounts,
                    with_moves=with_moves)

            logger.info('Calc vals for comparison period')
            initial_comparision_date = (comparison_start_period.start_date -
                timedelta(days=1))
            with transaction.set_context(date=initial_comparision_date):
                comparison_initial_values.update(
                    Account.read_account_vals(accounts, with_moves=with_moves))

        if split_parties:
            init_party_values = {}
            if add_initial_balance:
                logger.info('Calc initial values for parties')
                with transaction.set_context(date=initial_balance_date):
                    init_party_values = Party.get_account_values_by_party(
                        parties, accounts, fiscalyear.company)

            logger.info('Calc  values for parties')
            with transaction.set_context(fiscalyear=fiscalyear.id,
                    periods=periods):
                party_values = Party.get_account_values_by_party(
                    parties, accounts, fiscalyear.company)

            init_comparison_party_values = {}
            comparison_party_values = {}
            if comparison_fiscalyear:
                logger.info('Calc initial values for comparsion for parties')
                with transaction.set_context(date=initial_comparision_date):
                    init_comparison_party_values = \
                        Party.get_account_values_by_party(parties, accounts,
                            fiscalyear.company)

                logger.info('Calc values for comparsion for parties')
                with transaction.set_context(fiscalyear=fiscalyear.id,
                        periods=comparison_periods):
                    comparison_party_values = \
                        Party.get_account_values_by_party(parties, accounts,
                            fiscalyear.company)

        records = []
        virt_records = {}
        ok_records = []
        offset = 3000
        index = 0
        while index * offset < len(accounts):
            chunk = accounts[index * offset: (index + 1) * offset]
            index += 1
            for account in chunk:
                if digits and account.code:
                    if len(account.code.strip()) < digits:
                        continue
                    elif (len(account.code) == digits and
                            account.type == None):
                        account.kind = 'other'

                vals = _amounts(account, init_values, values)
                initial, credit, debit, balance = vals

                if with_moves_or_initial:
                    if credit == 0 and debit == 0 and initial == 0:
                        continue
                elif with_moves and credit == 0 and debit == 0:
                    continue

                comp_vals = _amounts(account,
                    comparison_initial_values, comparison_values)
                comp_initial, comp_credit, comp_debit, comp_balance = \
                    comp_vals

                if split_parties and account.party_required:
                    account_parties = parties
                    if not account_parties:
                        pids = set()
                        if account.id in party_values:
                            pids |= set(party_values[account.id].keys())
                        if account.id in init_party_values:
                            pids |= set(init_party_values[account.id].keys())
                        account_parties = [None] if None in pids else []
                        # Using search insted of browse to get ordered records
                        with transaction.set_context(active_test=False):
                            account_parties += Party.search([
                                    ('id', 'in', [p for p in pids if p])
                                    ])
                    for party in account_parties:
                        party_key = party.id if party else None
                        party_vals = _party_amounts(account,
                                party_key, init_party_values, party_values)
                        party_comp_vals = _party_amounts(account,
                                party_key, init_comparison_party_values,
                                comparison_party_values)
                        init, credit, debit, balance = party_vals

                        if with_moves_or_initial:
                            if credit == 0 and debit == 0 and initial == 0:
                                continue
                        elif with_moves and credit == 0 and debit == 0:
                            continue

                        record = _record(account, party,
                            party_vals, party_comp_vals, add_initial_balance)

                        records.append(record)
                        ok_records.append(account.code)
                else:
                    record = _record(account, None, vals, comp_vals,
                        add_initial_balance)
                    records.append(record)
                    ok_records.append(account.code)

            for record in virt_records:
                records.append(virt_records[record])

        logger.info('Records:' + str(len(records)))
        return records, parameters

    @classmethod
    def execute(cls, ids, data):
        records, parameters = cls.prepare(data)
        return super(TrialBalanceReport, cls).execute(ids, {
                'name': 'account_jasper_reports.trial_balance',
                'model': 'account.move.line',
                'data_source': 'records',
                'records': records,
                'parameters': parameters,
                'output_format': data['output_format'],
                })

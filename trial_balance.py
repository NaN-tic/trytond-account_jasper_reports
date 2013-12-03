#This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
#at the top level of this repository contains the full copyright notices and
#license terms.

from sql.aggregate import Sum
from sql.conditionals import Coalesce
from sql.operators import In
from decimal import Decimal
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import Eval, Bool
from trytond.tools import reduce_ids
from trytond.modules.jasper_reports.jasper import JasperReport
import logging

__all__ = ['PrintTrialBalanceStart', 'PrintTrialBalance',
    'TrialBalanceReport']

_ZERO = Decimal('0.00')


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
    add_initial_balance = fields.Boolean('Add Initial Balance')
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
            ('start_date', '<=', (Eval('comparison_end_period'),
                    'start_date')),
            ],
        states={
            'required': Bool(Eval('comparison_fiscalyear'))
        }, depends=['comparison_fiscalyear', 'comparison_end_period'])

    comparison_end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('comparison_fiscalyear')),
            ('start_date', '>=', (Eval('comparison_start_period'),
                    'start_date'))
            ],
        states={
            'required': Bool(Eval('comparison_fiscalyear'))
        },
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

    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }

    def on_change_comparison_fiscalyear(self):
        return {
            'comparison_start_period': None,
            'comparison_end_period': None,
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
            'add_initial_balance': self.start.add_initial_balance,
            'with_move_only': self.start.with_move_only,
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
            'all_accounts': not account_ids,
            'accounts': account_ids,
            'all_parties': not party_ids,
            'parties': party_ids,
            }


class TrialBalanceReport(JasperReport):
    __name__ = 'account_jasper_reports.trial_balance'

    @classmethod
    def read_account_vals(cls, accounts, with_moves=False):
        pool = Pool()
        Account = pool.get('account.account')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        line = MoveLine.__table__()
        move = Move.__table__()
        table_a = Account.__table__()
        table_c = Account.__table__()
        in_max = 3000
        values = {}
        transaction = Transaction()
        cursor = transaction.cursor
        move_join = 'INNER' if with_moves else 'LEFT'
        account_ids = [a.id for a in accounts]
        group_by = (table_a.id,)
        columns = (group_by + (Sum(Coalesce(line.debit, 0)).as_('debit'),
                Sum(Coalesce(line.credit, 0)).as_('credit'),
                (Sum(Coalesce(line.debit, 0)) -
                    Sum(Coalesce(line.credit, 0))).as_('balance')))
        for i in range(0, len(account_ids), in_max):
            sub_ids = account_ids[i:i + in_max]
            red_sql = reduce_ids(table_a.id, sub_ids)
            where = red_sql
            periods = transaction.context.get('periods', False)
            if periods:
                periods.append(0)
                where = (where & In(Coalesce(move.period, 0), periods))
            cursor.execute(*table_a.join(table_c,
                    condition=(table_c.left >= table_a.left)
                    & (table_c.right <= table_a.right)
                    ).join(line, move_join,
                        condition=line.account == table_c.id
                    ).join(move, move_join,
                        condition=move.id == line.move
                    ).select(*columns, where=where, group_by=group_by))

            for x in cursor.dictfetchall():
                values[x['id']] = {
                    'credit': x['credit'],
                    'debit': x['debit'],
                    'balance': x['balance'],
                    }
        return values

    @classmethod
    def execute(cls, ids, data):
        def _amounts(account, init_vals, vals):
            initial = init_vals.get(account.id, {}).get('balance') or _ZERO
            credit = vals.get(account.id, {}).get('credit') or _ZERO
            debit = vals.get(account.id, {}).get('debit') or _ZERO
            balance = vals.get(account.id, {}).get('balance') or _ZERO
            return initial, credit, debit, balance

        def _party_amounts(account, party, init_vals, vals):
            iac_vals = init_vals.get(account.id, {})
            ac_vals = vals.get(account.id, {})
            initial = iac_vals.get(party.id, {}).get('balance') or _ZERO
            credit = ac_vals.get(party.id, {}).get('credit') or _ZERO
            debit = ac_vals.get(party.id, {}).get('debit') or _ZERO
            balance = ac_vals.get(party.id, {}).get('balance') or _ZERO
            return initial, credit, debit, balance

        def _record(account, party, vals, comp, add_initial_balance):
            init, credit, debit, balance = vals
            init_comp, credit_comp, debit_comp, balance_comp = comp
            if add_initial_balance:
                balance += init
                balance_comp += init_comp
            return {
                'code': account.code,
                'name': party and party.name or account.name,
                'type': account.kind,
                'period_initial_balance': init,
                'period_credit': credit,
                'period_debit': debit,
                'period_balance': balance,
                'initial_balance': init_comp,
                'credit': credit_comp,
                'debit': debit_comp,
                'balance': balance_comp,
            }
        logger = logging.getLogger('account_jasper_reports')
        logger.info('Start Trial Balance')

        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        Period = pool.get('account.period')
        Account = pool.get('account.account')
        Party = pool.get('party.party')

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
        add_initial_balance = data['add_initial_balance']
        with_moves = data['with_move_only']

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
        parameters['SECOND_BALANCE'] = comparison_fiscalyear and True or False
        parameters['fiscalyear'] = fiscalyear.name
        parameters['comparison_fiscalyear'] = comparison_fiscalyear and \
            comparison_fiscalyear.name or ''
        parameters['start_period'] = start_period and start_period.name or ''
        parameters['end_period'] = end_period and end_period.name or ''
        parameters['comparison_start_period'] = comparison_start_period and\
            comparison_start_period.name or ''
        parameters['comparisonend_period'] = comparison_end_period and\
            comparison_end_period.name or ''
        parameters['digits'] = digits or ''
        parameters['with_moves_only'] = with_moves or ''
        parameters['split_parties'] = split_parties or ''

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
            if not digits or len(account.code) == digits or \
                account.kind != 'view' and len(account.childs) == 0 and \
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
        with Transaction().set_context(fiscalyear=fiscalyear.id,
                periods=periods):
            values = cls.read_account_vals(accounts, with_moves=with_moves)

        # Calc Initial Balance for first period
        initial_periods = [p.id for p in Period.search([
                    ('fiscalyear', '=', fiscalyear.id),
                    ('start_date', '<=', start_period.start_date),
                    ('end_date', '<', start_period.end_date),
            ])]

        init_values = {}
        if initial_periods:
            logger.info('Calc Initial Balance')
            with Transaction().set_context(periods=initial_periods):
                init_values = cls.read_account_vals(accounts,
                    with_moves=with_moves)

        # Calc comparison period values.
        comparison_initial_values = {}.fromkeys(accounts, Decimal('0.00'))
        comparison_values = {}.fromkeys(accounts, Decimal('0.00'))
        initial_comparison_periods = []

        if comparison_fiscalyear:
        #    second_dict = {}.fromkeys(accounts, Decimal('0.00'))
            logger.info('Calc initial vals for comparison period')
            with Transaction().set_context(periods=comparison_periods):
                comparison_values = cls.read_account_vals(accounts,
                    with_moves=with_moves)

            # Calc Initial Balance for comparison period
            initial_comparison_periods = Period.search([
                    ('fiscalyear', '=', comparison_fiscalyear.id),
                    ('start_date', '<=', comparison_start_period.start_date),
                    ('end_date', '<', comparison_end_period.end_date),
                ])

            logger.info('Calc vals for comparison period')
            with Transaction().set_context(periods=initial_comparison_periods):
                comparison_initial_values.update(
                    cls.read_account_vals(accounts, with_moves=with_moves))
        if split_parties:

            logger.info('Calc initial values for parties')
            with Transaction().set_context(fiscalyear=fiscalyear.id,
                    periods=initial_periods):
                init_party_values = Party.get_account_values_by_party(
                    parties, accounts)

            logger.info('Calc  values for parties')
            with Transaction().set_context(fiscalyear=fiscalyear.id,
                    periods=periods):
                party_values = Party.get_account_values_by_party(
                    parties, accounts)

            init_comparison_party_values = {}
            comparison_party_values = {}
            if comparison_fiscalyear:
                logger.info('Calc initial values for comparsion for parties')
                with Transaction().set_context(fiscalyear=fiscalyear.id,
                        periods=initial_comparison_periods):
                    init_comparison_party_values = \
                        Party.get_account_values_by_party(parties, accounts)

                logger.info('Calc values for comparsion for parties')
                with Transaction().set_context(fiscalyear=fiscalyear.id,
                        periods=comparison_periods):
                    comparison_party_values = \
                        Party.get_account_values_by_party(parties, accounts)

        records = []
        virt_records = {}
        ok_records = []
        offset = 3000
        index = 0
        while index * offset < len(accounts):
            chunk = accounts[index * offset: (index + 1) * offset]
            index += 1
            for account in chunk:
                if digits:
                    if len(account.code.strip()) < digits:
                        continue
                    elif len(account.code) == digits and account.kind == 'view':
                        account.kind = 'other'

                vals = _amounts(account, init_values, values)
                initial, credit, debit, balance = vals

                if with_moves and credit == 0 and debit == 0:
                    continue

                comp_vals = _amounts(account,
                    comparison_initial_values,  comparison_values)
                comp_initial, comp_credit, comp_debit, comp_balance = \
                    comp_vals

                if digits and len(account.code.strip()) != digits:
                    virt_code = account.code[:digits]
                    if virt_code in ok_records:
                        continue
                    record = virt_records.get(virt_code)
                    vr = virt_records.get(virt_code, {})
                    initial += vr.get('period_initial_balance', _ZERO)
                    comp_initial += vr.get('initial_balance', _ZERO)
                    balance += initial + vr.get('period_balance', _ZERO)
                    comp_balance += comp_initial + vr.get('balance', _ZERO)
                    credit += vr.get('period_credit', _ZERO)
                    debit += vr.get('period_debit', _ZERO)
                    comp_credit += vr.get('credit', _ZERO)
                    comp_debit += vr.get('debit', _ZERO)

                    record = {
                        'code': virt_code,
                        'name': '',
                        'type': 'fix',
                        'period_initial_balance': initial,
                        'period_credit': credit,
                        'period_debit': debit,
                        'period_balance': balance,
                        'initial_balance': comp_initial,
                        'credit': comp_credit,
                        'debit': comp_debit,
                        'balance': comp_balance,
                    }
                    virt_records[virt_code] = record
                    continue

                if split_parties and account.kind in ['payable', 'receivable']:
                    account_parties = parties
                    if not account_parties:
                        pids = set()
                        if account.id in party_values:
                            pids |= set(party_values[account.id].keys())
                        if account.id in init_party_values:
                            pids |= set(init_party_values[account.id].keys())
                        pids = [p for p in pids if p]
                        account_parties = Party.browse(list(pids))
                    for party in account_parties:
                        party_vals = _party_amounts(account,
                                party, init_party_values, party_values)
                        party_comp_vals = _party_amounts(account,
                                party, init_comparison_party_values,
                                comparison_party_values)
                        init, credit, debit, balance = party_vals

                        if with_moves and not debit and not credit and \
                                not balance:
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

        return super(TrialBalanceReport, cls).execute(ids, {
                'name': 'account_jasper_reports.trial_balance',
                'model': 'account.move.line',
                'data_source': 'records',
                'records': records,
                'parameters': parameters,
                'output_format': data['output_format'],

            })

#This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
#at the top level of this repository contains the full copyright notices and
#license terms.
from sql.aggregate import Sum
from sql.conditionals import Coalesce
from decimal import Decimal
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['FiscalYear', 'Party']
__metaclass__ = PoolMeta


class FiscalYear:
    'Fiscal Year'
    __name__ = 'account.fiscalyear'

    def get_periods(self, start_period, end_period):
        pool = Pool()
        Period = pool.get('account.period')
        domain = [('fiscalyear', '=', self)]
        if start_period:
            domain += [('start_date', '>=', start_period.start_date)]
            domain += [('end_date', '>=', start_period.end_date)]
        if end_period:
            domain += [('start_date', '<=', end_period.start_date)]
            domain += [('end_date', '<=', end_period.end_date)]

        periods = Period.search(domain)
        return periods


class Party:
    'Party'
    __name__ = 'party.party'

    @classmethod
    def get_account_values_by_party(cls, parties, accounts):
        '''
        Function to compute credit,debit and balance for party ids.
        '''
        res = {}
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        Account = pool.get('account.account')
        transaction = Transaction()
        cursor = transaction.cursor

        line = MoveLine.__table__()
        account = Account.__table__()

        company = transaction.context.get('company')
        if not company:
            return res

        group_by = (line.party, line.account,)
        columns = (group_by + (Sum(Coalesce(line.debit, 0)).as_('debit'),
                Sum(Coalesce(line.credit, 0)).as_('credit'),
                (Sum(Coalesce(line.debit, 0)) -
                    Sum(Coalesce(line.credit, 0))).as_('balance')))
        line_query, _ = MoveLine.query_get(line)
        where = (line_query & account.active &
            (account.company == company))
        if accounts:
            where = where & line.account.in_([a.id for a in accounts])
        if parties:
            where = where & line.party.in_([p.id for p in parties])
        cursor.execute(*line.join(account,
                condition=(line.account == account.id)
                ).select(*columns, where=where, group_by=group_by))

        for party, account, debit, credit, balance in cursor.fetchall():
            # SQLite uses float for SUM
            if not isinstance(credit, Decimal):
                credit = Decimal(str(credit))
            if not isinstance(debit, Decimal):
                debit = Decimal(str(debit))
            if not isinstance(balance, Decimal):
                balance = Decimal(str(balance))

            if account not in res:
                res[account] = {}
            res[account][party] = {
                    'credit': credit,
                    'debit': debit,
                    'balance': balance,
                }
        return res

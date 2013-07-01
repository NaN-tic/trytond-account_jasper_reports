#This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
#at the top level of this repository contains the full copyright notices and
#license terms.
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
        if end_period:
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
        User = pool.get('res.user')
        cursor = Transaction().cursor

        for name in [('credit', 'debit', 'balance')]:
            res[name] = dict((p.id, Decimal('0.0')) for p in parties)

        user_id = Transaction().user
        if user_id == 0 and 'user' in Transaction().context:
            user_id = Transaction().context['user']
        user = User(user_id)
        if not user.company:
            return res
        company_id = user.company.id

        line_query, _ = MoveLine.query_get()

        cursor.execute('SELECT l.party, '
                'a.id ',
                'SUM((COALESCE(l.debit, 0)) as credit ,'
                'SUM((COALESCE(.credit, 0)) ad debit ,'
                'SUM((COALESCE(l.debit, 0) - COALESCE(l.credit, 0))) '
            'FROM account_move_line AS l, account_account AS a '
            'WHERE a.id = l.account '
                'AND a.active '
                'AND a.id IN '
                    '(' + ','.join(('%s',) * len(accounts)) + ') '

                'AND l.party IN '
                    '(' + ','.join(('%s',) * len(parties)) + ') '
                'AND l.reconciliation IS NULL '
                'AND ' + line_query + ' '
                'AND a.company = %s '
            'GROUP BY l.account,l.party', [a.id for a in accounts] +
                [p.id for p in parties] + [company_id])

        for account_id, party_id, credit, debit, balance in cursor.fetchall():
            # SQLite uses float for SUM
            if not isinstance(credit, Decimal):
                credit = Decimal(str(credit))
            if not isinstance(debit, Decimal):
                debit = Decimal(str(debit))
            if not isinstance(balance, Decimal):
                balance = Decimal(str(balance))

            res[account_id] = {
                party_id: {
                    'credit': credit,
                    'debit': debit,
                    'balance': balance,
                },
            }

        return res

#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Reconciliation', 'Line']


class Reconciliation:
    'Account Move Reconciliation Lines'
    __name__ = 'account.move.reconciliation'
    __metaclass__ = PoolMeta

    date = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')

    def get_date(self, name):
        if self.lines:
            return max([line.date for line in self.lines])

    @classmethod
    def search_date(cls, name, clause):
        field, operator, value = clause
        if operator in ['<', '<=', '!=']:
            return [('lines.date', operator, value)]
        reconciliation_ids = []
        reconciliations = cls.search([('lines.date', operator, value)])
        for reconciliation in reconciliations:
            if reconciliation.date:
                if (operator == '=' and reconciliation.date == value or
                        operator == '>=' and reconciliation.date >= value or
                        operator == '>' and reconciliation.date > value):
                    reconciliation_ids.append(reconciliation.id)
        return [('id', 'in', reconciliation_ids)]


class Line:
    'Account Move Line'
    __name__ = 'account.move.line'
    __metaclass__ = PoolMeta

    reconciliation_date = fields.Function(fields.Date('Reconciliation Date'),
        'get_reconciliation_date', searcher='search_reconciliation_date')

    def get_reconciliation_date(self, name):
        if self.reconciliation:
            return self.reconciliation.date

    @classmethod
    def search_reconciliation_date(cls, name, clause):
        reconciliation_date_clause = ('reconciliation.date',) + tuple(clause[1:])
        if clause[1][0] == '>':
            return ['OR', ('reconciliation', '=', None),
                reconciliation_date_clause]
        else:
            return [reconciliation_date_clause]

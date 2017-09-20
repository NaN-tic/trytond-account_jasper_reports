#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Reconciliation']


class Reconciliation:
    'Account Move Reconciliation Lines'
    __name__ = 'account.move.reconciliation'
    __metaclass__ = PoolMeta

    date = fields.Function(fields.Date('Date'), 'get_date')

    def get_date(self, name):
        return max([line.date for line in self.lines])

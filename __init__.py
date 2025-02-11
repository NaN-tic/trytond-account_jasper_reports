# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import common
from . import abreviated_journal
from . import journal


def register():
    Pool.register(
        common.Account,
        common.Party,
        journal.PrintJournalStart,
        abreviated_journal.PrintAbreviatedJournalStart,
        common.FiscalYear,
        module='account_jasper_reports', type_='model')
    Pool.register(
        journal.PrintJournal,
        abreviated_journal.PrintAbreviatedJournal,
        module='account_jasper_reports', type_='wizard')
    Pool.register(
        journal.JournalReport,
        abreviated_journal.AbreviatedJournalReport,
        module='account_jasper_reports', type_='report')

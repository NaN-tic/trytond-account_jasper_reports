#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.pool import Pool
from .common import *
from .general_ledger import *
from .journal import *
from .trial_balance import *


def register():
    Pool.register(
        PrintJournalStart,
        PrintGeneralLedgerStart,
        PrintTrialBalanceStart,
        FiscalYear,
        Party,
        module='account_jasper_reports', type_='model')
    Pool.register(
        PrintJournal,
        PrintGeneralLedger,
        PrintTrialBalance,
        module='account_jasper_reports', type_='wizard')
    Pool.register(
        JournalReport,
        GeneralLedgerReport,
        TrialBalanceReport,
        module='account_jasper_reports', type_='report')


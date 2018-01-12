# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .common import *
from .general_ledger import *
from .abreviated_journal import *
from .journal import *
from .trial_balance import *
from .taxes_by_invoice import *
from .move import *
from .invoice import *


def register():
    Pool.register(
        Account,
        Party,
        PrintJournalStart,
        PrintAbreviatedJournalStart,
        PrintGeneralLedgerStart,
        PrintTrialBalanceStart,
        PrintTaxesByInvoiceAndPeriodStart,
        FiscalYear,
        Reconciliation,
        UnreconciledStart,
        Line,
        module='account_jasper_reports', type_='model')
    Pool.register(
        PrintJournal,
        PrintAbreviatedJournal,
        PrintGeneralLedger,
        PrintTrialBalance,
        PrintTaxesByInvoiceAndPeriod,
        Unreconciled,
        module='account_jasper_reports', type_='wizard')
    Pool.register(
        JournalReport,
        AbreviatedJournalReport,
        GeneralLedgerReport,
        TrialBalanceReport,
        TaxesByInvoiceReport,
        TaxesByInvoiceAndPeriodReport,
        module='account_jasper_reports', type_='report')

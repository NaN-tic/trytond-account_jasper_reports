# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import common
from . import general_ledger
from . import abreviated_journal
from . import journal
from . import trial_balance
from . import taxes_by_invoice


def register():
    Pool.register(
        common.Account,
        common.Party,
        journal.PrintJournalStart,
        abreviated_journal.PrintAbreviatedJournalStart,
        general_ledger.PrintGeneralLedgerStart,
        trial_balance.PrintTrialBalanceStart,
        taxes_by_invoice.PrintTaxesByInvoiceAndPeriodStart,
        common.FiscalYear,
        module='account_jasper_reports', type_='model')
    Pool.register(
        journal.PrintJournal,
        abreviated_journal.PrintAbreviatedJournal,
        general_ledger.PrintGeneralLedger,
        trial_balance.PrintTrialBalance,
        taxes_by_invoice.PrintTaxesByInvoiceAndPeriod,
        module='account_jasper_reports', type_='wizard')
    Pool.register(
        journal.JournalReport,
        abreviated_journal.AbreviatedJournalReport,
        general_ledger.GeneralLedgerReport,
        trial_balance.TrialBalanceReport,
        taxes_by_invoice.TaxesByInvoiceReport,
        taxes_by_invoice.TaxesByInvoiceAndPeriodReport,
        module='account_jasper_reports', type_='report')

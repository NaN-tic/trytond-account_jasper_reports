# This file is part of the account_jasper_reports module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import unittest
from trytond.pool import Pool
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction
from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear
from trytond.modules.account_invoice.tests import set_invoice_sequences


class AccountJasperReportsTestCase(ModuleTestCase):
    'Test Account Jasper Reports module'
    module = 'account_jasper_reports'

    def setUp(self):
        super(AccountJasperReportsTestCase, self).setUp()

    def create_fiscalyear_and_chart(self, company=None, fiscalyear=None,
            chart=True):
        'Test fiscalyear'
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        if not company:
            company = create_company()
        with set_company(company):
            if chart:
                create_chart(company)
            if not fiscalyear:
                fiscalyear = set_invoice_sequences(get_fiscalyear(company))
                fiscalyear.save()
                FiscalYear.create_period([fiscalyear])
                self.assertEqual(len(fiscalyear.periods), 12)
            return fiscalyear

    def get_journals(self):
        pool = Pool()
        Journal = pool.get('account.journal')
        return dict((j.code, j) for j in Journal.search([]))

    def get_accounts(self, company):
        pool = Pool()
        Account = pool.get('account.account')
        accounts_search = Account.search(['OR',
                ('type.receivable', '=', True),
                ('type.payable', '=', True),
                ('type.revenue', '=', True),
                ('type.expense', '=', True),
                ('company', '=', company.id),
                ])

        accounts = {}
        for kind in ('receivable', 'payable', 'revenue', 'expense'):
            accounts.update(
                {kind: a for a in accounts_search if a.type and getattr(
                        a.type, kind)})

        root, = Account.search([
                ('parent', '=', None),
                ('company', '=', company.id),
                ])
        accounts['root'] = root
        if not accounts['revenue'].code:
            accounts['revenue'].parent = root
            accounts['revenue'].code = '7'
            accounts['revenue'].save()
        if not accounts['receivable'].code:
            accounts['receivable'].parent = root
            accounts['receivable'].code = '43'
            accounts['receivable'].save()
        if not accounts['expense'].code:
            accounts['expense'].parent = root
            accounts['expense'].code = '6'
            accounts['expense'].save()
        if not accounts['payable'].code:
            accounts['payable'].parent = root
            accounts['payable'].code = '41'
            accounts['payable'].save()

        # TODO
        cash, = Account.search([
        #        ('kind', '=', 'other'),
                ('name', '=', 'Main Cash'),
                ('company', '=', company.id),
                ])
        accounts['cash'] = cash
        tax, = Account.search([
        #        ('kind', '=', 'other'),
                ('name', '=', 'Main Tax'),
                ('company', '=', company.id),
                ])
        accounts['tax'] = tax
        views = Account.search([
                ('name', '=', 'View'),
                ('company', '=', company.id),
                ])
        if views:
            view, = views
        else:
            with set_company(company):
                view, = Account.create([{
                            'name': 'View',
                            'code': '1',
                            'parent': root.id,
                            }])
        accounts['view'] = view
        return accounts

    def create_parties(self, company):
        pool = Pool()
        Party = pool.get('party.party')
        with set_company(company):
            return Party.create([{
                        'name': 'customer1',
                        'addresses': [('create', [{}])],
                    }, {
                        'name': 'customer2',
                        'addresses': [('create', [{}])],
                    }, {
                        'name': 'supplier1',
                        'addresses': [('create', [{}])],
                    }, {
                        'name': 'supplier2',
                        'addresses': [('create', [{'active': False}])],
                        'active': False,
                    }])

    def get_parties(self):
        pool = Pool()
        Party = pool.get('party.party')
        customer1, = Party.search([
                ('name', '=', 'customer1'),
                ])
        customer2, = Party.search([
                ('name', '=', 'customer2'),
                ])
        supplier1, = Party.search([
                ('name', '=', 'supplier1'),
                ])
        with Transaction().set_context(active_test=False):
            supplier2, = Party.search([
                    ('name', '=', 'supplier2'),
                    ])
        return customer1, customer2, supplier1, supplier2

    def create_moves(self, company, fiscalyear=None, create_chart=True):
        'Create moves some moves for the test'
        pool = Pool()
        Move = pool.get('account.move')
        fiscalyear = self.create_fiscalyear_and_chart(company, fiscalyear,
            create_chart)
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        journals = self.get_journals()
        journal_revenue = journals['REV']
        journal_expense = journals['EXP']
        accounts = self.get_accounts(company)
        revenue = accounts['revenue']
        receivable = accounts['receivable']
        expense = accounts['expense']
        payable = accounts['payable']
        # Create some parties
        if create_chart:
            customer1, customer2, supplier1, supplier2 = self.create_parties(
                company)
        else:
            customer1, customer2, supplier1, supplier2 = self.get_parties()
        # Create some moves
        vlist = [
            {
                'company': company.id,
                'period': period.id,
                'journal': journal_revenue.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(100),
                                }, {
                                'party': customer1.id,
                                'account': receivable.id,
                                'debit': Decimal(100),
                                }]),
                    ],
                },
            {
                'company': company.id,
                'period': period.id,
                'journal': journal_revenue.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(200),
                                }, {
                                'party': customer2.id,
                                'account': receivable.id,
                                'debit': Decimal(200),
                                }]),
                    ],
                },
            {
                'company': company.id,
                'period': period.id,
                'journal': journal_expense.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(30),
                                }, {
                                'party': supplier1.id,
                                'account': payable.id,
                                'credit': Decimal(30),
                                }]),
                    ],
                },
            {
                'company': company.id,
                'period': period.id,
                'journal': journal_expense.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(50),
                                }, {
                                'party': supplier2.id,
                                'account': payable.id,
                                'credit': Decimal(50),
                                }]),
                    ],
                },
            {
                'company': company.id,
                'period': last_period.id,
                'journal': journal_expense.id,
                'date': last_period.end_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(50),
                                }, {
                                'party': supplier2.id,
                                'account': payable.id,
                                'credit': Decimal(50),
                                }]),
                    ],
                },
            {
                'company': company.id,
                'period': last_period.id,
                'journal': journal_revenue.id,
                'date': last_period.end_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(300),
                                }, {
                                'party': customer2.id,
                                'account': receivable.id,
                                'debit': Decimal(300),
                                }]),
                    ],
                },
            ]
        moves = Move.create(vlist)
        Move.post(moves)
        # Set account inactive
        expense.active = False
        expense.save()
        return fiscalyear

    @with_transaction()
    def test_journal(self):
        'Test journal'
        pool = Pool()
        PrintJournal = pool.get('account_jasper_reports.print_journal',
            type='wizard')
        JournalReport = pool.get('account_jasper_reports.journal',
            type='report')
        company = create_company()
        fiscalyear = self.create_moves(company)
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        journals = self.get_journals()
        journal_revenue = journals['REV']
        journal_expense = journals['EXP']
        session_id, _, _ = PrintJournal.create()
        print_journal = PrintJournal(session_id)
        print_journal.start.company = company
        print_journal.start.fiscalyear = fiscalyear
        print_journal.start.start_period = period
        print_journal.start.end_period = last_period
        print_journal.start.journals = []
        print_journal.start.output_format = 'pdf'
        print_journal.start.open_close_account_moves = False
        print_journal.start.open_move_description = 'Open'
        print_journal.start.close_move_description = 'Close'

        _, data = print_journal.do_print_(None)
        # Full Journall
        self.assertEqual(data['company'], company.id)
        self.assertEqual(data['fiscalyear'], fiscalyear.id)
        self.assertEqual(data['start_period'], period.id)
        self.assertEqual(data['end_period'], last_period.id)
        self.assertEqual(len(data['journals']), 0)
        self.assertEqual(data['output_format'], 'pdf')
        records, parameters = JournalReport.prepare(data)
        self.assertEqual(len(records), 12)
        self.assertEqual(parameters['start_period'], period.name)
        self.assertEqual(parameters['end_period'], last_period.name)
        self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
        self.assertEqual(parameters['journals'], '')
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, debit)
        self.assertEqual(credit, Decimal('730.0'))
        with_party = [m for m in records if m['party_name']]
        self.assertEqual(len(with_party), 6)
        # Filtering periods
        session_id, _, _ = PrintJournal.create()
        print_journal = PrintJournal(session_id)
        print_journal.start.company = company
        print_journal.start.fiscalyear = fiscalyear
        print_journal.start.start_period = period
        print_journal.start.end_period = period
        print_journal.start.journals = []
        print_journal.start.output_format = 'pdf'
        print_journal.start.open_close_account_moves = False
        print_journal.start.open_move_description = 'Open'
        print_journal.start.close_move_description = 'Close'

        _, data = print_journal.do_print_(None)
        records, parameters = JournalReport.prepare(data)
        self.assertEqual(len(records), 8)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, debit)
        self.assertEqual(credit, Decimal('380.0'))
        # Filtering journals
        journals = self.get_journals()
        journal_revenue = journals['REV']
        journal_expense = journals['EXP']
        session_id, _, _ = PrintJournal.create()
        print_journal = PrintJournal(session_id)
        print_journal.start.company = company
        print_journal.start.fiscalyear = fiscalyear
        print_journal.start.start_period = period
        print_journal.start.end_period = period
        print_journal.start.journals = [journal_revenue, journal_expense]
        print_journal.start.output_format = 'pdf'
        print_journal.start.open_close_account_moves = False
        print_journal.start.open_move_description = 'Open'
        print_journal.start.close_move_description = 'Close'
        _, data = print_journal.do_print_(None)
        records, parameters = JournalReport.prepare(data)
        self.assertNotEqual(parameters['journals'], '')
        self.assertEqual(len(records), 8)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, debit)
        self.assertEqual(credit, Decimal('380.0'))

    @with_transaction()
    def test_abreviated_journal(self):
        'Test journal'
        pool = Pool()
        PrintAbreviatedJournal = pool.get(
            'account_jasper_reports.print_abreviated_journal', type='wizard')
        AbreviatedJournalReport = pool.get(
            'account_jasper_reports.abreviated_journal', type='report')
        company = create_company()
        fiscalyear = self.create_moves(company)
        period = fiscalyear.periods[0]
        session_id, _, _ = PrintAbreviatedJournal.create()
        print_abreviated_journal = PrintAbreviatedJournal(
            session_id)
        print_abreviated_journal.start.company = company
        print_abreviated_journal.start.fiscalyear = fiscalyear
        print_abreviated_journal.start.display_account = 'bal_all'
        print_abreviated_journal.start.level = 1
        print_abreviated_journal.start.output_format = 'pdf'
        _, data = print_abreviated_journal.do_print_(None)
        self.assertEqual(data['company'], company.id)
        self.assertEqual(data['fiscalyear'], fiscalyear.id)
        self.assertEqual(data['display_account'], 'bal_all')
        self.assertEqual(data['level'], 1)
        self.assertEqual(data['output_format'], 'pdf')
        records, parameters = AbreviatedJournalReport.prepare(data)
        self.assertEqual(len(records), 3 * 12)
        self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(debit, 130.0)
        self.assertEqual(credit, 600.0)
        credit = sum([m['credit'] for m in records
                if m['month'] == period.rec_name])
        debit = sum([m['debit'] for m in records
                if m['month'] == period.rec_name])
        self.assertEqual(debit, 80.0)
        self.assertEqual(credit, 300.0)
        # Only with moves
        print_abreviated_journal = PrintAbreviatedJournal(
            session_id)
        print_abreviated_journal.start.company = company
        print_abreviated_journal.start.fiscalyear = fiscalyear
        print_abreviated_journal.start.display_account = 'bal_movement'
        print_abreviated_journal.start.level = 1
        print_abreviated_journal.start.output_format = 'pdf'
        _, data = print_abreviated_journal.do_print_(None)
        records, parameters = AbreviatedJournalReport.prepare(data)
        self.assertEqual(len(records), 4)
        # With two digits
        session_id, _, _ = PrintAbreviatedJournal.create()
        print_abreviated_journal = PrintAbreviatedJournal(
            session_id)
        print_abreviated_journal.start.company = company
        print_abreviated_journal.start.fiscalyear = fiscalyear
        print_abreviated_journal.start.display_account = 'bal_all'
        print_abreviated_journal.start.level = 2
        print_abreviated_journal.start.output_format = 'pdf'
        _, data = print_abreviated_journal.do_print_(None)
        records, parameters = AbreviatedJournalReport.prepare(data)
        self.assertEqual(len(records), 4 * 12)
        # With two digits and movements
        session_id, _, _ = PrintAbreviatedJournal.create()
        print_abreviated_journal = PrintAbreviatedJournal(
            session_id)
        print_abreviated_journal.start.company = company
        print_abreviated_journal.start.fiscalyear = fiscalyear
        print_abreviated_journal.start.display_account = 'bal_movement'
        print_abreviated_journal.start.level = 2
        print_abreviated_journal.start.output_format = 'pdf'
        _, data = print_abreviated_journal.do_print_(None)
        records, parameters = AbreviatedJournalReport.prepare(data)
        self.assertEqual(len(records), 4 * 2)

    @with_transaction()
    def test_general_ledger(self):
        'Test General Ledger'
        pool = Pool()
        Account = pool.get('account.account')
        PrintGeneralLedger = pool.get(
            'account_jasper_reports.print_general_ledger', type='wizard')
        GeneralLedgerReport = pool.get(
            'account_jasper_reports.general_ledger', type='report')
        company = create_company()
        fiscalyear = self.create_moves(company)
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        session_id, _, _ = PrintGeneralLedger.create()
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = fiscalyear
        print_general_ledger.start.start_period = period
        print_general_ledger.start.end_period = last_period
        print_general_ledger.start.start_date = None
        print_general_ledger.start.end_date = None
        print_general_ledger.start.parties = []
        print_general_ledger.start.accounts = []
        print_general_ledger.start.output_format = 'pdf'
        print_general_ledger.start.all_accounts = False
        _, data = print_general_ledger.do_print_(None)

        # Full general_ledger
        self.assertEqual(data['company'], company.id)
        self.assertEqual(data['fiscalyear'], fiscalyear.id)
        self.assertEqual(data['start_period'], period.id)
        self.assertEqual(data['end_period'], last_period.id)
        self.assertEqual(len(data['accounts']), 0)
        self.assertEqual(len(data['parties']), 0)
        self.assertEqual(data['output_format'], 'pdf')
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(len(records), 12)
        self.assertEqual(parameters['start_period'], period.name)
        self.assertEqual(parameters['end_period'], last_period.name)
        self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
        self.assertEqual(parameters['accounts'], '')
        self.assertEqual(parameters['parties'], '')
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, debit)
        self.assertEqual(credit, Decimal('730.0'))
        with_party = [m for m in records if m['party_name'] != '']
        self.assertEqual(len(with_party), 6)
        dates = sorted(set([r['date'] for r in records]))
        for date, expected_value in zip(dates, [period.start_date,
                    last_period.end_date]):
            self.assertEqual(date, expected_value.strftime('%d/%m/%Y'))

        # Filtered by periods
        session_id, _, _ = PrintGeneralLedger.create()
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = fiscalyear
        print_general_ledger.start.start_period = period
        print_general_ledger.start.end_period = period
        print_general_ledger.start.start_date = None
        print_general_ledger.start.end_date = None
        print_general_ledger.start.parties = []
        print_general_ledger.start.accounts = []
        print_general_ledger.start.all_accounts = False
        print_general_ledger.start.output_format = 'pdf'
        _, data = print_general_ledger.do_print_(None)
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(len(records), 8)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, debit)
        self.assertEqual(credit, Decimal('380.0'))
        dates = [r['date'] for r in records]
        for date in dates:
            self.assertEqual(date, period.start_date.strftime('%d/%m/%Y'))

        # Filtered by dates
        session_id, _, _ = PrintGeneralLedger.create()
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = None
        print_general_ledger.start.start_period = None
        print_general_ledger.start.end_period = None
        print_general_ledger.start.start_date = period.start_date
        print_general_ledger.start.end_date = period.end_date
        print_general_ledger.start.parties = []
        print_general_ledger.start.accounts = []
        print_general_ledger.start.all_accounts = False
        print_general_ledger.start.output_format = 'pdf'
        _, data = print_general_ledger.do_print_(None)
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(len(records), 8)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, debit)
        self.assertEqual(credit, Decimal('380.0'))
        dates = [r['date'] for r in records]
        for date in dates:
            self.assertEqual(date, period.start_date.strftime('%d/%m/%Y'))

        # Filtered by accounts
        expense, = Account.search([
                ('type.expense', '=', True),
                ])
        session_id, _, _ = PrintGeneralLedger.create()
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = fiscalyear
        print_general_ledger.start.start_period = period
        print_general_ledger.start.end_period = last_period
        print_general_ledger.start.start_date = None
        print_general_ledger.start.end_date = None
        print_general_ledger.start.parties = []
        print_general_ledger.start.accounts = [expense.id]
        print_general_ledger.start.all_accounts = False
        print_general_ledger.start.output_format = 'pdf'
        _, data = print_general_ledger.do_print_(None)
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(parameters['accounts'], expense.code)
        self.assertEqual(len(records), 3)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, Decimal('0.0'))
        self.assertEqual(debit, Decimal('130.0'))

        # Filter by parties
        customer1 = self.get_parties()[0]
        session_id, _, _ = PrintGeneralLedger.create()
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = fiscalyear
        print_general_ledger.start.start_period = period
        print_general_ledger.start.end_period = last_period
        print_general_ledger.start.start_date = None
        print_general_ledger.start.end_date = None
        print_general_ledger.start.parties = [customer1.id]
        print_general_ledger.start.accounts = []
        print_general_ledger.start.all_accounts = False
        print_general_ledger.start.output_format = 'pdf'
        _, data = print_general_ledger.do_print_(None)
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(parameters['parties'], customer1.rec_name)
        self.assertEqual(len(records), 1)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, Decimal('0.0'))
        self.assertEqual(debit, Decimal('100.0'))
        credit = sum([m['credit'] for m in records
                if m['party_name'] == ''])
        debit = sum([m['debit'] for m in records
                if m['party_name'] == ''])
        self.assertEqual(credit, Decimal('0.0'))
        self.assertEqual(debit, Decimal('0.0'))

        # Filter by parties and accounts
        receivable, = Account.search([
                ('type.receivable', '=', True),
                ])
        session_id, _, _ = PrintGeneralLedger.create()
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = fiscalyear
        print_general_ledger.start.start_period = period
        print_general_ledger.start.end_period = last_period
        print_general_ledger.start.start_date = None
        print_general_ledger.start.end_date = None
        print_general_ledger.start.parties = [customer1.id]
        print_general_ledger.start.accounts = [receivable.id]
        print_general_ledger.start.output_format = 'pdf'
        print_general_ledger.start.all_accounts = False
        _, data = print_general_ledger.do_print_(None)
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(parameters['parties'], customer1.rec_name)
        self.assertEqual(parameters['accounts'], receivable.code)
        self.assertEqual(len(records), 1)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, Decimal('0.0'))
        self.assertEqual(debit, Decimal('100.0'))
        self.assertEqual(True, all(m['party_name'] != ''
                for m in records))

        # Check balance of full general_ledger
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = fiscalyear
        print_general_ledger.start.start_period = None
        print_general_ledger.start.end_period = None
        print_general_ledger.start.start_date = None
        print_general_ledger.start.end_date = None
        print_general_ledger.start.parties = []
        print_general_ledger.start.accounts = []
        print_general_ledger.start.output_format = 'pdf'
        print_general_ledger.start.all_accounts = False
        _, data = print_general_ledger.do_print_(None)
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(len(records), 12)
        balances = [
            Decimal('30'),             # Expense
            Decimal('80'),             # Expense
            Decimal('130'),            # Expense
            Decimal('-30'),            # Payable Party 1
            Decimal('-50'),            # Payable Party 2
            Decimal('-100'),           # Payable Party 2
            Decimal('100'),            # Receivable Party 1
            Decimal('200'),            # Receivable Party 2
            Decimal('500'),            # Receivable Party 2
            Decimal('-100'),           # Revenue
            Decimal('-300'),           # Revenue
            Decimal('-600'),           # Revenue
            ]
        for record, balance in zip(records, balances):
            self.assertEqual(record['balance'], balance)

    @with_transaction()
    def test_trial_balance(self):
        'Test Trial Balance'
        pool = Pool()
        PrintTrialBalance = pool.get(
            'account_jasper_reports.print_trial_balance', type='wizard')
        TrialBalanceReport = pool.get(
            'account_jasper_reports.trial_balance', type='report')
        company = create_company()
        fiscalyear = self.create_moves(company)
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # Full trial_balance
        self.assertEqual(data['company'], company.id)
        self.assertEqual(data['fiscalyear'], fiscalyear.id)
        self.assertEqual(data['start_period'], period.id)
        self.assertEqual(data['end_period'], last_period.id)
        self.assertEqual(len(data['accounts']), 0)
        self.assertEqual(len(data['parties']), 0)
        self.assertEqual(data['output_format'], 'pdf')
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 7)
        self.assertEqual(parameters['start_period'], period.name)
        self.assertEqual(parameters['end_period'], last_period.name)
        self.assertEqual(parameters['fiscalyear'], fiscalyear.name)
        self.assertEqual(parameters['accounts'], '')
        self.assertEqual(parameters['parties'], '')
        self.assertEqual(parameters['with_moves_only'], '')
        self.assertEqual(parameters['split_parties'], '')
        self.assertEqual(parameters['second_balance'], False)
        self.assertEqual(parameters['comparison_fiscalyear'], '')
        self.assertEqual(parameters['comparison_start_period'], '')
        self.assertEqual(parameters['comparison_end_period'], '')
        self.assertEqual(parameters['total_period_credit'], '730,00')
        self.assertEqual(parameters['total_period_balance'], '0,00')
        self.assertEqual(parameters['total_credit'], '0,00')
        self.assertEqual(parameters['total_balance'], '0,00')
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = 1
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # With 1 digit
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 3)
        self.assertEqual(parameters['total_period_credit'], '600,00')
        self.assertEqual(parameters['total_period_debit'], '130,00')
        self.assertEqual(parameters['total_period_balance'], '-470,00')
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = 2
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # With 2 digits
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 2)
        self.assertEqual(parameters['total_period_credit'], '130,00')
        self.assertEqual(parameters['total_period_debit'], '600,00')
        self.assertEqual(parameters['total_period_balance'], '470,00')
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = 1
        print_trial_balance.start.with_move_only = True
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # With 1 digits and only with moves
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 2)
        self.assertEqual(parameters['with_moves_only'], True)
        self.assertEqual(parameters['total_period_credit'], '600,00')
        self.assertEqual(parameters['total_period_debit'], '130,00')
        self.assertEqual(parameters['total_period_balance'], '-470,00')
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = 2
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # With 2 digits and splited with parties
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 4)
        self.assertEqual(parameters['split_parties'], True)
        self.assertEqual(parameters['total_period_credit'], '130,00')
        self.assertEqual(parameters['total_period_debit'], '600,00')
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # Full splited with parties
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 9)
        self.assertEqual(parameters['split_parties'], True)
        self.assertEqual(parameters['total_period_credit'], '730,00')
        self.assertEqual(parameters['total_period_debit'], '730,00')
        customer1 = self.get_parties()[0]
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = [customer1.id]
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # Customer 1 and splited with parties
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 7)
        self.assertEqual(parameters['parties'], customer1.rec_name)
        self.assertEqual(parameters['total_period_debit'], '230,00')
        self.assertEqual(parameters['total_period_credit'], '600,00')
        self.assertEqual(parameters['total_period_balance'], '-370,00')
        revenue = self.get_accounts(company)['revenue']
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = [revenue.id]
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # Only revenue account
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 1)
        self.assertEqual(parameters['accounts'], revenue.code)
        self.assertEqual(parameters['total_period_credit'], '600,00')
        self.assertEqual(parameters['total_period_debit'], '0,00')
        self.assertEqual(parameters['total_period_balance'], '-600,00')
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = last_period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = True
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = True
        print_trial_balance.start.comparison_fiscalyear = fiscalyear
        print_trial_balance.start.comparison_start_period = last_period
        print_trial_balance.start.comparison_end_period = last_period
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # With moves and add initial balance
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 4)
        initial = parameters['total_period_initial_balance']
        self.assertEqual(parameters['total_period_credit'], '350,00')
        self.assertEqual(parameters['total_period_debit'], '350,00')
        results = {
            '41': ('-80,00', '-130,00'),
            '43': ('300,00', '600,00'),
            '6': ('80,00', '130,00'),
            '7': ('-300,00', '-600,00'),
            }
        for r in records:
            initial, balance = results[r['code']]
            self.assertEqual(r['period_initial_balance'], initial)
            self.assertEqual(r['period_balance'], balance)
            self.assertEqual(r['initial_balance'], initial)
            self.assertEqual(r['balance'], balance)
        for initial, balance in [(m['period_initial_balance'],
                    m['period_balance']) for m in records]:
            self.assertNotEqual(initial, '0,00')
            self.assertNotEqual(balance, '0,00')
            self.assertNotEqual(balance, initial)
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = last_period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = True
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = True
        print_trial_balance.start.comparison_fiscalyear = fiscalyear
        print_trial_balance.start.comparison_start_period = last_period
        print_trial_balance.start.comparison_end_period = last_period
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # With moves, split parties and add initial balance
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 4)
        results = {
            '41': ('-50,00', '-100,00'),
            '43': ('200,00', '500,00'),
            '6': ('80,00', '130,00'),
            '7': ('-300,00', '-600,00'),
            }
        for r in records:
            initial, balance = results[r['code']]
            self.assertEqual(r['period_initial_balance'], initial)
            self.assertEqual(r['period_balance'], balance)
            self.assertEqual(r['initial_balance'], initial)
            self.assertEqual(r['balance'], balance)
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = last_period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = True
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = fiscalyear
        print_trial_balance.start.comparison_start_period = period
        print_trial_balance.start.comparison_end_period = period
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # With moves and comparing period
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(parameters['comparison_fiscalyear'],
            fiscalyear.rec_name)
        self.assertEqual(parameters['comparison_start_period'],
            period.rec_name)
        self.assertEqual(parameters['comparison_end_period'],
            period.rec_name)
        self.assertEqual(len(records), 4)
        credit = parameters['total_period_credit']
        debit = parameters['total_period_debit']
        balance = parameters['total_period_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '350,00')
        self.assertEqual(balance, '0,00')
        # Comparision data
        credit = parameters['total_credit']
        debit = parameters['total_debit']
        balance = parameters['total_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '380,00')
        self.assertEqual(balance, '0,00')
        receivable = self.get_accounts(company)['receivable']
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = last_period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = [receivable.id]
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = True
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # Splited by parties but move doesn't have any party defined
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 1)
        self.assertEqual(parameters['accounts'], receivable.code)
        credit = parameters['total_credit']
        debit = parameters['total_debit']
        balance = parameters['total_balance']
        self.assertEqual(debit, '0,00')
        self.assertEqual(credit, '0,00')
        self.assertEqual(balance, '0,00')
        # Inactive customers should always apear on trial balance
        customer1.active = False
        customer1.save()
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = None
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        # Full splited with parties
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 9)
        self.assertEqual(parameters['split_parties'], True)
        credit = parameters['total_period_credit']
        debit = parameters['total_period_debit']
        balance = parameters['total_period_balance']
        self.assertEqual(debit, '730,00')
        self.assertEqual(credit, '730,00')
        # If we do not indicate periods we get the full definition
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = fiscalyear
        print_trial_balance.start.start_period = None
        print_trial_balance.start.end_period = None
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = False
        print_trial_balance.start.add_initial_balance = False
        print_trial_balance.start.comparison_fiscalyear = fiscalyear
        print_trial_balance.start.comparison_start_period = None
        print_trial_balance.start.comparison_end_period = None
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)
        self.assertEqual(data['start_period'], period.id)
        self.assertEqual(data['end_period'], last_period.id)
        self.assertEqual(data['comparison_start_period'], period.id)
        self.assertEqual(data['comparison_end_period'], last_period.id)
        records, parameters = TrialBalanceReport.prepare(data)
        self.assertEqual(len(records), 7)
        self.assertEqual(parameters['start_period'], period.name)
        self.assertEqual(parameters['end_period'], last_period.name)
        self.assertEqual(parameters['fiscalyear'], fiscalyear.name)
        credit = parameters['total_period_credit']
        debit = parameters['total_period_debit']
        balance = parameters['total_period_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '730,00')
        self.assertEqual(credit, '730,00')
        credit = parameters['total_credit']
        debit = parameters['total_debit']
        balance = parameters['total_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '730,00')
        self.assertEqual(credit, '730,00')

    @with_transaction()
    def test_taxes_by_invoice(self):
        'Test taxes by invoice'
        pool = Pool()
        Date = pool.get('ir.date')
        PaymentTerm = pool.get('account.invoice.payment_term')
        TaxCode = pool.get('account.tax.code')
        Tax = pool.get('account.tax')
        Invoice = pool.get('account.invoice')
        InvoiceTax = pool.get('account.invoice.tax')
        PrintTaxesByInvoice = pool.get(
            'account_jasper_reports.print_taxes_by_invoice', type='wizard')
        TaxesByInvoiceReport = pool.get(
            'account_jasper_reports.taxes_by_invoice', type='report')

        company = create_company()
        fiscalyear = self.create_moves(company)
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        accounts = self.get_accounts(company)
        revenue = accounts['revenue']
        receivable = accounts['receivable']
        expense = accounts['expense']
        payable = accounts['payable']
        account_tax = accounts['tax']
        journals = self.get_journals()
        journal_revenue = journals['REV']
        journal_expense = journals['EXP']

        term, = PaymentTerm.create([{
                    'name': 'Payment term',
                    'lines': [
                        ('create', [{
                                    'type': 'remainder',
                                    'relativedeltas': [
                                        ('create', [{
                                                    'sequence': 0,
                                                    'days': 0,
                                                    'months': 0,
                                                    'weeks': 0,
                                                    }])],
                                    }])],
                    }])

        with set_company(company):
            tx = TaxCode.create([{
                            'name': 'invoice base',
                            },
                        {
                            'name': 'invoice tax',
                            },
                        {
                            'name': 'credit note base',
                            },
                        {
                            'name': 'credit note tax',
                        }])
            invoice_base, invoice_tax, credit_note_base, credit_note_tax = tx
            tax1, tax2 = Tax.create([{
                        'name': 'Tax 1',
                        'description': 'Tax 1',
                        'type': 'percentage',
                        'rate': Decimal('.10'),
                        'invoice_account': account_tax.id,
                        'credit_note_account': account_tax.id,
                        },
                    {
                        'name': 'Tax 2',
                        'description': 'Tax 2',
                        'type': 'percentage',
                        'rate': Decimal('.04'),
                        'invoice_account': account_tax.id,
                        'credit_note_account': account_tax.id,
                        }])
            customer, _, supplier, supplier2 = self.get_parties()
            customer_address, = customer.addresses
            supplier_address, = supplier.addresses
            invoices = Invoice.create([{
                        'number': '1',
                        'invoice_date': period.start_date,
                        'company': company.id,
                        'type': 'out',
                        'currency': company.currency.id,
                        'party': customer.id,
                        'invoice_address': customer_address.id,
                        'journal': journal_revenue.id,
                        'account': receivable.id,
                        'payment_term': term.id,
                        'payment_term_date': Date.today(),
                        'lines': [
                            ('create', [{
                                        'invoice_type': 'out',
                                        'type': 'line',
                                        'sequence': 0,
                                        'description': 'invoice_line',
                                        'account': revenue.id,
                                        'quantity': 1,
                                        'unit_price': Decimal('50.0'),
                                        'taxes': [
                                            ('add', [tax1.id, tax2.id])],
                                        }])],
                        },
                    {
                        'number': '2',
                        'invoice_date': period.start_date,
                        'company': company.id,
                        'type': 'in',
                        'currency': company.currency.id,
                        'party': supplier.id,
                        'invoice_address': supplier_address.id,
                        'journal': journal_expense.id,
                        'account': payable.id,
                        'payment_term': term.id,
                        'payment_term_date': Date.today(),
                        'lines': [
                            ('create', [{
                                        'invoice_type': 'in',
                                        'type': 'line',
                                        'sequence': 0,
                                        'description': 'invoice_line',
                                        'account': expense.id,
                                        'quantity': 1,
                                        'unit_price': Decimal('20.0'),
                                        'taxes': [
                                            ('add', [tax1.id, tax2.id])],
                                        }])],
                        },
                    ])
            Invoice.post(invoices)
        invoice1, invoice2 = invoices
        session_id, _, _ = PrintTaxesByInvoice.create()
        print_taxes_by_invoice = PrintTaxesByInvoice(session_id)
        print_taxes_by_invoice.start.company = company
        print_taxes_by_invoice.start.fiscalyear = fiscalyear
        print_taxes_by_invoice.start.periods = []
        print_taxes_by_invoice.start.parties = []
        print_taxes_by_invoice.start.partner_type = 'customers'
        print_taxes_by_invoice.start.grouping = 'invoice'
        print_taxes_by_invoice.start.totals_only = False
        print_taxes_by_invoice.start.start_date = None
        print_taxes_by_invoice.start.end_date = None
        print_taxes_by_invoice.start.tax_type = 'all'
        print_taxes_by_invoice.start.output_format = 'pdf'
        print_taxes_by_invoice.start.taxes = []
        _, data = print_taxes_by_invoice.do_print_(None)
        # Customer data
        self.assertEqual(data['company'], company.id)
        self.assertEqual(data['fiscalyear'], fiscalyear.id)
        self.assertEqual(data['partner_type'], 'customers')
        self.assertEqual(data['grouping'], 'invoice')
        self.assertEqual(data['totals_only'], False)
        self.assertEqual(len(data['periods']), 0)
        self.assertEqual(len(data['parties']), 0)
        self.assertEqual(len(data['taxes']), 0)
        self.assertEqual(data['output_format'], 'pdf')
        ids, parameters = TaxesByInvoiceReport.prepare(data)
        records = InvoiceTax.browse(ids)
        self.assertEqual(len(records), 2)
        self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
        self.assertEqual(parameters['parties'], '')
        self.assertEqual(parameters['periods'], '')
        self.assertEqual(parameters['TOTALS_ONLY'], False)
        base = sum([m.company_base for m in records])
        tax = sum([m.company_amount for m in records])
        self.assertEqual(base, Decimal('100.0'))
        self.assertEqual(tax, Decimal('7.0'))
        for tax in records:
            self.assertEqual(tax.invoice, invoice1)
        session_id, _, _ = PrintTaxesByInvoice.create()
        print_taxes_by_invoice = PrintTaxesByInvoice(session_id)
        print_taxes_by_invoice.start.company = company
        print_taxes_by_invoice.start.fiscalyear = fiscalyear
        print_taxes_by_invoice.start.periods = []
        print_taxes_by_invoice.start.parties = []
        print_taxes_by_invoice.start.partner_type = 'suppliers'
        print_taxes_by_invoice.start.grouping = 'invoice'
        print_taxes_by_invoice.start.totals_only = False
        print_taxes_by_invoice.start.start_date = None
        print_taxes_by_invoice.start.end_date = None
        print_taxes_by_invoice.start.tax_type = 'all'
        print_taxes_by_invoice.start.output_format = 'pdf'
        print_taxes_by_invoice.start.taxes = []
        _, data = print_taxes_by_invoice.do_print_(None)
        # Supplier data
        ids, parameters = TaxesByInvoiceReport.prepare(data)
        records = InvoiceTax.browse(ids)
        self.assertEqual(len(records), 2)
        base = sum([m.company_base for m in records])
        tax = sum([m.company_amount for m in records])
        self.assertEqual(base, Decimal('40.0'))
        self.assertEqual(tax, Decimal('2.8'))
        for tax in records:
            self.assertEqual(tax.invoice, invoice2)
        session_id, _, _ = PrintTaxesByInvoice.create()
        print_taxes_by_invoice = PrintTaxesByInvoice(session_id)
        print_taxes_by_invoice.start.company = company
        print_taxes_by_invoice.start.fiscalyear = fiscalyear
        print_taxes_by_invoice.start.periods = []
        print_taxes_by_invoice.start.parties = [supplier2.id]
        print_taxes_by_invoice.start.partner_type = 'suppliers'
        print_taxes_by_invoice.start.grouping = 'invoice'
        print_taxes_by_invoice.start.totals_only = False
        print_taxes_by_invoice.start.output_format = 'pdf'
        print_taxes_by_invoice.start.start_date = None
        print_taxes_by_invoice.start.tax_type = 'all'
        print_taxes_by_invoice.start.end_date = None
        print_taxes_by_invoice.start.taxes = []
        _, data = print_taxes_by_invoice.do_print_(None)
        # Filter by supplier
        ids, parameters = TaxesByInvoiceReport.prepare(data)
        self.assertEqual(parameters['parties'], supplier2.rec_name)
        records = InvoiceTax.browse(ids)
        self.assertEqual(len(records), 0)
        session_id, _, _ = PrintTaxesByInvoice.create()
        print_taxes_by_invoice = PrintTaxesByInvoice(session_id)
        print_taxes_by_invoice.start.company = company
        print_taxes_by_invoice.start.fiscalyear = fiscalyear
        print_taxes_by_invoice.start.periods = [last_period.id]
        print_taxes_by_invoice.start.parties = []
        print_taxes_by_invoice.start.partner_type = 'suppliers'
        print_taxes_by_invoice.start.grouping = 'invoice'
        print_taxes_by_invoice.start.totals_only = False
        print_taxes_by_invoice.start.output_format = 'pdf'
        print_taxes_by_invoice.start.start_date = None
        print_taxes_by_invoice.start.end_date = None
        print_taxes_by_invoice.start.tax_type = 'all'
        print_taxes_by_invoice.start.taxes = []
        _, data = print_taxes_by_invoice.do_print_(None)
        # Filter by periods
        ids, parameters = TaxesByInvoiceReport.prepare(data)
        self.assertEqual(parameters['periods'], last_period.rec_name)
        records = InvoiceTax.browse(ids)
        self.assertEqual(len(records), 0)
        # Filter by start/end date
        session_id, _, _ = PrintTaxesByInvoice.create()
        print_taxes_by_invoice = PrintTaxesByInvoice(session_id)
        print_taxes_by_invoice.start.company = company
        print_taxes_by_invoice.start.fiscalyear = fiscalyear
        print_taxes_by_invoice.start.periods = []
        print_taxes_by_invoice.start.parties = []
        print_taxes_by_invoice.start.partner_type = 'customers'
        print_taxes_by_invoice.start.grouping = 'invoice'
        print_taxes_by_invoice.start.totals_only = False
        print_taxes_by_invoice.start.start_date = period.start_date
        print_taxes_by_invoice.start.end_date = period.end_date
        print_taxes_by_invoice.start.output_format = 'pdf'
        print_taxes_by_invoice.start.tax_type = 'all'
        print_taxes_by_invoice.start.taxes = []
        _, data = print_taxes_by_invoice.do_print_(None)
        ids, parameters = TaxesByInvoiceReport.prepare(data)
        self.assertEqual(parameters['start_date'],
            period.start_date.strftime('%d/%m/%Y'))
        self.assertEqual(parameters['end_date'],
            period.end_date.strftime('%d/%m/%Y'))
        records = InvoiceTax.browse(ids)
        self.assertEqual(len(records), 2)

    @with_transaction()
    def test_fiscalyear_not_closed(self):
        'Test fiscalyear not closed'
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        PrintGeneralLedger = pool.get(
            'account_jasper_reports.print_general_ledger', type='wizard')
        GeneralLedgerReport = pool.get(
            'account_jasper_reports.general_ledger', type='report')
        PrintTrialBalance = pool.get(
            'account_jasper_reports.print_trial_balance', type='wizard')
        TrialBalanceReport = pool.get(
            'account_jasper_reports.trial_balance', type='report')
        company = create_company()

        fiscalyear = self.create_moves(company)
        fiscalyear.save()
        with set_company(company):
            next_fiscalyear = set_invoice_sequences(get_fiscalyear(company,
                today=fiscalyear.end_date + relativedelta(days=1)))
        next_fiscalyear.save()
        FiscalYear.create_period([next_fiscalyear])
        self.create_moves(company, next_fiscalyear, False)

        # General ledger for the next year
        period = next_fiscalyear.periods[0]
        last_period = next_fiscalyear.periods[-1]
        session_id, _, _ = PrintGeneralLedger.create()
        print_general_ledger = PrintGeneralLedger(session_id)
        print_general_ledger.start.company = company
        print_general_ledger.start.fiscalyear = next_fiscalyear
        print_general_ledger.start.start_period = period
        print_general_ledger.start.end_period = last_period
        print_general_ledger.start.start_date = None
        print_general_ledger.start.end_date = None
        print_general_ledger.start.parties = []
        print_general_ledger.start.accounts = []
        print_general_ledger.start.all_accounts = True
        print_general_ledger.start.output_format = 'pdf'
        _, data = print_general_ledger.do_print_(None)
        records, parameters = GeneralLedgerReport.prepare(data)
        self.assertEqual(len(records), 12)
        self.assertEqual(parameters['start_period'], period.name)
        self.assertEqual(parameters['end_period'], last_period.name)
        self.assertEqual(parameters['fiscal_year'], next_fiscalyear.name)
        self.assertEqual(parameters['accounts'], '')
        self.assertEqual(parameters['parties'], '')
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(credit, debit)
        self.assertEqual(credit, Decimal('730.0'))
        with_party = [m for m in records if m['party_name'] != '']
        self.assertEqual(len(with_party), 6)
        dates = sorted(set([r['date'] for r in records]))
        for date, expected_value in zip(dates, [period.start_date,
                    last_period.end_date]):
            self.assertEqual(date, expected_value.strftime('%d/%m/%Y'))
        balances = [
            Decimal('30'),            # Expense
            Decimal('80'),            # Expense
            Decimal('130'),            # Expense
            Decimal('-60'),            # Payable Party 1
            Decimal('-150'),           # Payable Party 2
            Decimal('-200'),           # Payable Party 2
            Decimal('200'),            # Receivable Party 1
            Decimal('700'),            # Receivable Party 2
            Decimal('1000'),           # Receivable Party 2
            Decimal('-100'),           # Revenue
            Decimal('-300'),           # Revenue
            Decimal('-600'),          # Revenue
            ]
        for record, balance in zip(records, balances):
            self.assertEqual(record['balance'], balance)

        # Trial for the next year
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = next_fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = True
        print_trial_balance.start.comparison_fiscalyear = next_fiscalyear
        print_trial_balance.start.comparison_start_period = period
        print_trial_balance.start.comparison_end_period = last_period
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)

        # Full trial_balance
        records, parameters = TrialBalanceReport.prepare(data)
        balances = {
            'Main Cash': '0,00',
            'Main Tax': '0,00',
            'View': '0,00',
            'supplier1': '-30,00',
            'supplier2': '-100,00',
            'customer1': '100,00',
            'customer2': '500,00',
            'Main Expense': '130,00',
            'Main Revenue': '-600,00',
            }
        for record in records:
            self.assertEqual(record['period_initial_balance'],
                balances[record['name']])
            self.assertEqual(record['initial_balance'],
                balances[record['name']])

        # Create another fiscalyear and test it cumulates correctly
        with set_company(company):
            future_fiscalyear = set_invoice_sequences(get_fiscalyear(company,
                today=fiscalyear.end_date + relativedelta(days=1, years=1)))
            future_fiscalyear.save()
        FiscalYear.create_period([future_fiscalyear])
        self.create_moves(company, future_fiscalyear, False)

        period = future_fiscalyear.periods[0]
        last_period = future_fiscalyear.periods[-1]
        session_id, _, _ = PrintTrialBalance.create()
        print_trial_balance = PrintTrialBalance(session_id)
        print_trial_balance.start.company = company
        print_trial_balance.start.fiscalyear = future_fiscalyear
        print_trial_balance.start.start_period = period
        print_trial_balance.start.end_period = last_period
        print_trial_balance.start.parties = []
        print_trial_balance.start.accounts = []
        print_trial_balance.start.show_digits = None
        print_trial_balance.start.with_move_only = False
        print_trial_balance.start.with_move_or_initial = False
        print_trial_balance.start.split_parties = True
        print_trial_balance.start.add_initial_balance = True
        print_trial_balance.start.comparison_fiscalyear = future_fiscalyear
        print_trial_balance.start.comparison_start_period = period
        print_trial_balance.start.comparison_end_period = last_period
        print_trial_balance.start.output_format = 'pdf'
        _, data = print_trial_balance.do_print_(None)

        # Full trial_balance
        records, parameters = TrialBalanceReport.prepare(data)
        balances = {
            'Main Cash': '0,00',
            'Main Tax': '0,00',
            'View': '0,00',
            'supplier1': '-60,00',
            'supplier2': '-200,00',
            'customer1': '200,00',
            'customer2': '1.000,00',
            'Main Expense': '260,00',
            'Main Revenue': '-1.200,00',
            }
        for record in records:
            self.assertEqual(record['period_initial_balance'],
                balances[record['name']])
            self.assertEqual(record['initial_balance'],
                balances[record['name']])


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountJasperReportsTestCase))
    return suite

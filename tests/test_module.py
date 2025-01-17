# This file is part of the account_jasper_reports module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction
from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear
from trytond.modules.account_invoice.tests import set_invoice_sequences
from trytond.modules.company.tests import CompanyTestMixin


class AccountJasperReportsTestCase(CompanyTestMixin, ModuleTestCase):
    'Test AccountJasperReports module'
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

        views = Account.search([
                ('name', '=', 'View'),
                ('company', '=', company.id),
                ], limit=1)
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
        print_abreviated_journal.start.level = 5
        print_abreviated_journal.start.output_format = 'pdf'
        _, data = print_abreviated_journal.do_print_(None)
        self.assertEqual(data['company'], company.id)
        self.assertEqual(data['fiscalyear'], fiscalyear.id)
        self.assertEqual(data['display_account'], 'bal_all')
        self.assertEqual(data['level'], print_abreviated_journal.start.level)
        self.assertEqual(data['output_format'], 'pdf')
        records, parameters = AbreviatedJournalReport.prepare(data)
        # self.assertEqual(len(records), 3 * 12)
        self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
        credit = sum([m['credit'] for m in records])
        debit = sum([m['debit'] for m in records])
        self.assertEqual(debit, 2190.0)
        self.assertEqual(credit, 2190.0)
        credit = sum([m['credit'] for m in records
                if m['month'] == period.rec_name])
        debit = sum([m['debit'] for m in records
                if m['month'] == period.rec_name])
        self.assertEqual(debit, 1140.0)
        self.assertEqual(credit, 1140.0)
        # Only with moves
        print_abreviated_journal = PrintAbreviatedJournal(
            session_id)
        print_abreviated_journal.start.company = company
        print_abreviated_journal.start.fiscalyear = fiscalyear
        print_abreviated_journal.start.display_account = 'bal_movement'
        print_abreviated_journal.start.level = 5
        print_abreviated_journal.start.output_format = 'pdf'
        _, data = print_abreviated_journal.do_print_(None)
        records, parameters = AbreviatedJournalReport.prepare(data)
        self.assertEqual(len(records), 24)
        # With two digits
        session_id, _, _ = PrintAbreviatedJournal.create()
        print_abreviated_journal = PrintAbreviatedJournal(
            session_id)
        print_abreviated_journal.start.company = company
        print_abreviated_journal.start.fiscalyear = fiscalyear
        print_abreviated_journal.start.display_account = 'bal_all'
        print_abreviated_journal.start.level = 5
        print_abreviated_journal.start.output_format = 'pdf'
        _, data = print_abreviated_journal.do_print_(None)
        records, parameters = AbreviatedJournalReport.prepare(data)
        self.assertEqual(len(records), 1584)

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
        self.assertEqual(len(records), 135)
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
        self.assertEqual(parameters['total_period_credit'], '2.190,00')
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
        print_trial_balance.start.show_digits = 5
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
        self.assertEqual(len(records), 132)
        self.assertEqual(parameters['total_period_credit'], '2.190,00')
        self.assertEqual(parameters['total_period_debit'], '2.190,00')
        self.assertEqual(parameters['total_period_balance'], '0,00')

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
        self.assertEqual(len(records), 133)
        self.assertEqual(parameters['split_parties'], True)
        self.assertEqual(parameters['total_period_credit'], '2.190,00')
        self.assertEqual(parameters['total_period_debit'], '2.190,00')

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
        self.assertEqual(len(records), 135)
        self.assertEqual(parameters['parties'], customer1.rec_name)
        self.assertEqual(parameters['total_period_debit'], '1.690,00')
        self.assertEqual(parameters['total_period_credit'], '2.060,00')
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
        self.assertEqual(len(records), 12)
        initial = parameters['total_period_initial_balance']
        self.assertEqual(parameters['total_period_credit'], '1.050,00')
        self.assertEqual(parameters['total_period_debit'], '1.050,00')
        results = {
            '1.0.0': ('300,00', '600,00'),
            '1.2.0': ('300,00', '600,00'),
            '1.2.3': ('300,00', '600,00'),
            '2.0.0': ('-80,00', '-130,00'),
            '2.1.0': ('-80,00', '-130,00'),
            '2.1.4': ('-80,00', '-130,00'),
            '4.0.0': ('-300,00', '-600,00'),
            '4.3.0': ('-300,00', '-600,00'),
            '4.3.3': ('-300,00', '-600,00'),
            '5.0.0': ('80,00', '130,00'),
            '5.2.0': ('80,00', '130,00'),
            '5.2.3': ('80,00', '130,00'),
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
        self.assertEqual(len(records), 12)
        results = {
            '1.0.0': ('300,00', '600,00'),
            '1.2.0': ('300,00', '600,00'),
            '1.2.3': ('200,00', '500,00'),
            '2.0.0': ('-80,00', '-130,00'),
            '2.1.0': ('-80,00', '-130,00'),
            '2.1.4': ('-50,00', '-100,00'),
            '4.0.0': ('-300,00', '-600,00'),
            '4.3.0': ('-300,00', '-600,00'),
            '4.3.3': ('-300,00', '-600,00'),
            '5.0.0': ('80,00', '130,00'),
            '5.2.0': ('80,00', '130,00'),
            '5.2.3': ('80,00', '130,00'),
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
        self.assertEqual(len(records), 12)
        credit = parameters['total_period_credit']
        debit = parameters['total_period_debit']
        balance = parameters['total_period_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '1.050,00')
        self.assertEqual(balance, '0,00')
        # Comparision data
        credit = parameters['total_credit']
        debit = parameters['total_debit']
        balance = parameters['total_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '1.140,00')
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
        self.assertEqual(len(records), 133)
        self.assertEqual(parameters['split_parties'], True)
        credit = parameters['total_period_credit']
        debit = parameters['total_period_debit']
        balance = parameters['total_period_balance']
        self.assertEqual(debit, '2.190,00')
        self.assertEqual(credit, '2.190,00')

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
        self.assertEqual(len(records), 135)
        self.assertEqual(parameters['start_period'], period.name)
        self.assertEqual(parameters['end_period'], last_period.name)
        self.assertEqual(parameters['fiscalyear'], fiscalyear.name)
        credit = parameters['total_period_credit']
        debit = parameters['total_period_debit']
        balance = parameters['total_period_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '2.190,00')
        self.assertEqual(credit, '2.190,00')
        credit = parameters['total_credit']
        debit = parameters['total_debit']
        balance = parameters['total_balance']
        self.assertEqual(credit, debit)
        self.assertEqual(debit, '2.190,00')
        self.assertEqual(credit, '2.190,00')

    @with_transaction()
    def test_fiscalyear_not_closed(self):
        'Test fiscalyear not closed'
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
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

        period = next_fiscalyear.periods[0]
        last_period = next_fiscalyear.periods[-1]

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
        # balances = ["'%s': '%s'" % (record['name'], record['period_initial_balance'])
        #    for record in records if record['period_initial_balance'] != '0,00']
        balances = {
            'Assets': '600,00',
            'Receivables And Contracts': '600,00',
            'customer1': '100,00',
            'customer2': '500,00',
            'Liabilities': '-130,00',
            'Payables': '-130,00',
            'supplier1': '-30,00',
            'supplier2': '-100,00',
            'Revenue': '-600,00',
            'Adjustments': '-600,00',
            'Other Adjustments': '-600,00',
            'Expenses': '130,00',
            'Expenses Classified By Function': '130,00',
            'Credit Loss (Reversal) On Receivables': '130,00',
            }
        for record in records:
            if not balances.get(record['name']):
                continue
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
        # balances = ["'%s': '%s'" % (record['name'], record['period_initial_balance'])
        #    for record in records if record['period_initial_balance'] != '0,00']
        balances = {
            'Assets': '1.200,00',
            'Receivables And Contracts': '1.200,00',
            'customer1': '200,00', 'customer2': '1.000,00',
            'Liabilities': '-260,00',
            'Payables': '-260,00',
            'supplier1': '-60,00',
            'supplier2': '-200,00',
            'Revenue': '-1.200,00',
            'Adjustments': '-1.200,00',
            'Other Adjustments': '-1.200,00',
            'Expenses': '260,00',
            'Expenses Classified By Function': '260,00',
            'Credit Loss (Reversal) On Receivables': '260,00',
            }
        for record in records:
            if not balances.get(record['name']):
                continue
            self.assertEqual(record['period_initial_balance'],
                balances[record['name']])
            self.assertEqual(record['initial_balance'],
                balances[record['name']])



del ModuleTestCase

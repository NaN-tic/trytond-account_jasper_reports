# This file is part of the account_jasper_reports module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
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

del ModuleTestCase

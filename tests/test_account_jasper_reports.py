#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import datetime
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class AccountJasperReportsTestCase(unittest.TestCase):
    'Test Account Jasper Reports module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('account_jasper_reports')
        self.account = POOL.get('account.account')
        self.company = POOL.get('company.company')
        self.user = POOL.get('res.user')
        self.party = POOL.get('party.party')
        self.party_address = POOL.get('party.address')
        self.fiscalyear = POOL.get('account.fiscalyear')
        self.move = POOL.get('account.move')
        self.line = POOL.get('account.move.line')
        self.journal = POOL.get('account.journal')
        self.period = POOL.get('account.period')
        self.sequence = POOL.get('ir.sequence')
        self.sequence_strict = POOL.get('ir.sequence.strict')
        self.taxcode = POOL.get('account.tax.code')
        self.tax = POOL.get('account.tax')
        self.invoice = POOL.get('account.invoice')
        self.invoice_tax = POOL.get('account.invoice.tax')
        self.payment_term = POOL.get('account.invoice.payment_term')
        self.print_journal = POOL.get('account_jasper_reports.print_journal',
            type='wizard')
        self.journal_report = POOL.get('account_jasper_reports.journal',
            type='report')
        self.print_abreviated_journal = POOL.get(
            'account_jasper_reports.print_abreviated_journal', type='wizard')
        self.abreviated_journal_report = POOL.get(
            'account_jasper_reports.abreviated_journal', type='report')
        self.print_general_ledger = POOL.get(
            'account_jasper_reports.print_general_ledger', type='wizard')
        self.general_ledger_report = POOL.get(
            'account_jasper_reports.general_ledger', type='report')
        self.print_trial_balance = POOL.get(
            'account_jasper_reports.print_trial_balance', type='wizard')
        self.trial_balance_report = POOL.get(
            'account_jasper_reports.trial_balance', type='report')
        self.print_taxes_by_invoice = POOL.get(
            'account_jasper_reports.print_taxes_by_invoice', type='wizard')
        self.taxes_by_invoice_report = POOL.get(
            'account_jasper_reports.taxes_by_invoice', type='report')

    def test0005views(self):
        'Test views'
        test_view('account_jasper_reports')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def create_moves(self, fiscalyear=None):
        'Create moves for running tests'
        if not fiscalyear:
            fiscalyear, = self.fiscalyear.search([])
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        journal_revenue, = self.journal.search([
                ('code', '=', 'REV'),
                ])
        journal_expense, = self.journal.search([
                ('code', '=', 'EXP'),
                ])
        chart, = self.account.search([
                ('parent', '=', None),
                ])
        revenue, = self.account.search([
                ('kind', '=', 'revenue'),
                ])
        revenue.parent = chart
        revenue.code = '7'
        revenue.save()
        receivable, = self.account.search([
                ('kind', '=', 'receivable'),
                ])
        receivable.parent = chart
        receivable.code = '43'
        receivable.save()
        expense, = self.account.search([
                ('kind', '=', 'expense'),
                ])
        expense.parent = chart
        expense.code = '6'
        expense.save()
        payable, = self.account.search([
                ('kind', '=', 'payable'),
                ])
        payable.parent = chart
        payable.code = '41'
        payable.save()
        self.account.create([{
                    'name': 'View',
                    'code': '1',
                    'kind': 'view',
                    'parent': chart.id,
                    }])
        #Create some parties if not exist
        if self.party.search([('name', '=', 'customer1')]):
            customer1, = self.party.search([('name', '=', 'customer1')])
            customer2, = self.party.search([('name', '=', 'customer2')])
            supplier1, = self.party.search([('name', '=', 'supplier1')])
            with Transaction().set_context(active_test=False):
                supplier2, = self.party.search([('name', '=', 'supplier2')])
        else:
            customer1, customer2, supplier1, supplier2 = self.party.create([{
                        'name': 'customer1',
                        }, {
                        'name': 'customer2',
                        }, {
                        'name': 'supplier1',
                        }, {
                        'name': 'supplier2',
                        'active': False,
                        }])
            self.party_address.create([{
                            'active': True,
                            'party': customer1.id,
                        }, {
                            'active': True,
                            'party': supplier1.id,
                        }])
        # Create some moves
        vlist = [
            {
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
        moves = self.move.create(vlist)
        self.move.post(moves)
        # Set account inactive
        expense.active = False
        expense.save()

    def test0010journal(self):
        'Test journal'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.create_moves()
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin')])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]
            last_period = fiscalyear.periods[-1]
            session_id, _, _ = self.print_journal.create()
            print_journal = self.print_journal(session_id)
            print_journal.start.company = company
            print_journal.start.fiscalyear = fiscalyear
            print_journal.start.start_period = period
            print_journal.start.end_period = last_period
            print_journal.start.journals = []
            print_journal.start.output_format = 'pdf'
            _, data = print_journal.do_print_(None)
            #Full Journall
            self.assertEqual(data['company'], company.id)
            self.assertEqual(data['fiscalyear'], fiscalyear.id)
            self.assertEqual(data['start_period'], period.id)
            self.assertEqual(data['end_period'], last_period.id)
            self.assertEqual(len(data['journals']), 0)
            self.assertEqual(data['output_format'], 'pdf')
            ids, parameters = self.journal_report.prepare(data)
            records = self.line.browse(ids)
            self.assertEqual(len(records), 12)
            self.assertEqual(parameters['start_period'], period.name)
            self.assertEqual(parameters['end_period'], last_period.name)
            self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
            self.assertEqual(parameters['journals'], '')
            credit = sum([m.credit for m in records])
            debit = sum([m.debit for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('730.0'))
            with_party = [m for m in records if m.party]
            self.assertEqual(len(with_party), 6)
            #Filtering periods
            session_id, _, _ = self.print_journal.create()
            print_journal = self.print_journal(session_id)
            print_journal.start.company = company
            print_journal.start.fiscalyear = fiscalyear
            print_journal.start.start_period = period
            print_journal.start.end_period = period
            print_journal.start.journals = []
            print_journal.start.output_format = 'pdf'
            _, data = print_journal.do_print_(None)
            ids, parameters = self.journal_report.prepare(data)
            records = self.line.browse(ids)
            self.assertEqual(len(records), 8)
            credit = sum([m.credit for m in records])
            debit = sum([m.debit for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('380.0'))
            #Filtering journals
            journal_revenue, = self.journal.search([
                    ('code', '=', 'REV'),
                    ])
            journal_expense, = self.journal.search([
                    ('code', '=', 'EXP'),
                    ])
            session_id, _, _ = self.print_journal.create()
            print_journal = self.print_journal(session_id)
            print_journal.start.company = company
            print_journal.start.fiscalyear = fiscalyear
            print_journal.start.start_period = period
            print_journal.start.end_period = period
            print_journal.start.journals = [journal_revenue, journal_expense]
            print_journal.start.output_format = 'pdf'
            _, data = print_journal.do_print_(None)
            ids, parameters = self.journal_report.prepare(data)
            records = self.line.browse(ids)
            self.assertNotEqual(parameters['journals'], '')
            self.assertEqual(len(records), 8)
            credit = sum([m.credit for m in records])
            debit = sum([m.debit for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('380.0'))

    def test0020abreviated_journal(self):
        'Test journal'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.create_moves()
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin')])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]
            session_id, _, _ = self.print_abreviated_journal.create()
            print_abreviated_journal = self.print_abreviated_journal(
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
            records, parameters = self.abreviated_journal_report.prepare(data)
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
            #Only with moves
            print_abreviated_journal = self.print_abreviated_journal(
                session_id)
            print_abreviated_journal.start.company = company
            print_abreviated_journal.start.fiscalyear = fiscalyear
            print_abreviated_journal.start.display_account = 'bal_movement'
            print_abreviated_journal.start.level = 1
            print_abreviated_journal.start.output_format = 'pdf'
            _, data = print_abreviated_journal.do_print_(None)
            records, parameters = self.abreviated_journal_report.prepare(data)
            self.assertEqual(len(records), 4)
            #With two digits
            session_id, _, _ = self.print_abreviated_journal.create()
            print_abreviated_journal = self.print_abreviated_journal(
                session_id)
            print_abreviated_journal.start.company = company
            print_abreviated_journal.start.fiscalyear = fiscalyear
            print_abreviated_journal.start.display_account = 'bal_all'
            print_abreviated_journal.start.level = 2
            print_abreviated_journal.start.output_format = 'pdf'
            _, data = print_abreviated_journal.do_print_(None)
            records, parameters = self.abreviated_journal_report.prepare(data)
            self.assertEqual(len(records), 4 * 12)
            #With two digits and movements
            session_id, _, _ = self.print_abreviated_journal.create()
            print_abreviated_journal = self.print_abreviated_journal(
                session_id)
            print_abreviated_journal.start.company = company
            print_abreviated_journal.start.fiscalyear = fiscalyear
            print_abreviated_journal.start.display_account = 'bal_movement'
            print_abreviated_journal.start.level = 2
            print_abreviated_journal.start.output_format = 'pdf'
            _, data = print_abreviated_journal.do_print_(None)
            records, parameters = self.abreviated_journal_report.prepare(data)
            self.assertEqual(len(records), 4 * 2)

    def test0030general_ledger(self):
        'Test General Ledger'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.create_moves()
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin')])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]
            last_period = fiscalyear.periods[-1]
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.company = company
            print_general_ledger.start.fiscalyear = fiscalyear
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = []
            print_general_ledger.start.accounts = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)

            # Full general_ledger
            self.assertEqual(data['company'], company.id)
            self.assertEqual(data['fiscalyear'], fiscalyear.id)
            self.assertEqual(data['start_period'], period.id)
            self.assertEqual(data['end_period'], last_period.id)
            self.assertEqual(len(data['accounts']), 0)
            self.assertEqual(len(data['parties']), 0)
            self.assertEqual(data['output_format'], 'pdf')
            records, parameters = self.general_ledger_report.prepare(data)
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
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.company = company
            print_general_ledger.start.fiscalyear = fiscalyear
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = period
            print_general_ledger.start.parties = []
            print_general_ledger.start.accounts = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
            self.assertEqual(len(records), 8)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('380.0'))
            dates = [r['date'] for r in records]
            for date in dates:
                self.assertEqual(date, period.start_date.strftime('%d/%m/%Y'))
            #Filtered by accounts
            expense, = self.account.search([
                    ('kind', '=', 'expense'),
                    ])
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.company = company
            print_general_ledger.start.fiscalyear = fiscalyear
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = []
            print_general_ledger.start.accounts = [expense.id]
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
            self.assertEqual(parameters['accounts'], expense.code)
            self.assertEqual(len(records), 3)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(debit, Decimal('130.0'))
            #Filter by parties
            customer1, = self.party.search([
                    ('name', '=', 'customer1'),
                    ])
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.company = company
            print_general_ledger.start.fiscalyear = fiscalyear
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = [customer1.id]
            print_general_ledger.start.accounts = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
            self.assertEqual(parameters['parties'], customer1.rec_name)
            self.assertEqual(len(records), 7)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, Decimal('600.0'))
            self.assertEqual(debit, Decimal('230.0'))
            credit = sum([m['credit'] for m in records
                    if m['party_name'] != ''])
            debit = sum([m['debit'] for m in records
                    if m['party_name'] != ''])
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(debit, Decimal('100.0'))

            # Filter by parties and accounts
            receivable, = self.account.search([
                    ('kind', '=', 'receivable'),
                    ])
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.company = company
            print_general_ledger.start.fiscalyear = fiscalyear
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = [customer1.id]
            print_general_ledger.start.accounts = [receivable.id]
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
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
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.company = company
            print_general_ledger.start.fiscalyear = fiscalyear
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = []
            print_general_ledger.start.accounts = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
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

    def test0040trial_balance(self):
        'Test Trial Balance'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.create_moves()
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin')])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]
            last_period = fiscalyear.periods[-1]
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #Full trial_balance
            self.assertEqual(data['company'], company.id)
            self.assertEqual(data['fiscalyear'], fiscalyear.id)
            self.assertEqual(data['start_period'], period.id)
            self.assertEqual(data['end_period'], last_period.id)
            self.assertEqual(len(data['accounts']), 0)
            self.assertEqual(len(data['parties']), 0)
            self.assertEqual(data['output_format'], 'pdf')
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 7)
            self.assertEqual(parameters['start_period'], period.name)
            self.assertEqual(parameters['end_period'], last_period.name)
            self.assertEqual(parameters['fiscalyear'], fiscalyear.name)
            self.assertEqual(parameters['accounts'], '')
            self.assertEqual(parameters['parties'], '')
            self.assertEqual(parameters['digits'], '')
            self.assertEqual(parameters['with_moves_only'], '')
            self.assertEqual(parameters['split_parties'], '')
            self.assertEqual(parameters['SECOND_BALANCE'], False)
            self.assertEqual(parameters['comparison_fiscalyear'], '')
            self.assertEqual(parameters['comparison_start_period'], '')
            self.assertEqual(parameters['comparison_end_period'], '')
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('730.0'))
            self.assertEqual(balance, Decimal('0.0'))
            #Comparision data
            credit = sum([Decimal(str(m['credit'])) for m in records])
            debit = sum([Decimal(str(m['debit'])) for m in records])
            balance = sum([Decimal(str(m['balance'])) for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, balance)
            self.assertEqual(balance, Decimal('0.0'))
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #With 1 digit
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 3)
            self.assertEqual(parameters['digits'], 1)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, Decimal('600.0'))
            self.assertEqual(debit, Decimal('130.0'))
            self.assertEqual(balance, Decimal('-470.0'))
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #With 2 digits
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 2)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, Decimal('130.0'))
            self.assertEqual(debit, Decimal('600.0'))
            self.assertEqual(balance, Decimal('470.0'))
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #With 1 digits and only with moves
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 2)
            self.assertEqual(parameters['with_moves_only'], True)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(debit, Decimal('130.0'))
            self.assertEqual(credit, Decimal('600.0'))
            self.assertEqual(balance, Decimal('-470.0'))
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #With 2 digits and splited with parties
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 4)
            self.assertEqual(parameters['split_parties'], True)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, Decimal('130.0'))
            self.assertEqual(debit, Decimal('600.0'))
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #Full splited with parties
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 9)
            self.assertEqual(parameters['split_parties'], True)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, Decimal('730.0'))
            self.assertEqual(debit, Decimal('730.0'))
            customer1, = self.party.search([
                    ('name', '=', 'customer1'),
                    ])
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #Customer 1 and splited with parties
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 7)
            self.assertEqual(parameters['parties'], customer1.rec_name)
            credit = sum([Decimal(str(m['period_credit'])) for m in records
                    if m['name'] == customer1.rec_name])
            debit = sum([Decimal(str(m['period_debit'])) for m in records
                    if m['name'] == customer1.rec_name])
            balance = sum([Decimal(str(m['period_balance'])) for m in records
                    if m['name'] == customer1.rec_name])
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(debit, Decimal('100.0'))
            self.assertEqual(balance, Decimal('100.0'))
            revenue, = self.account.search([
                    ('kind', '=', 'revenue'),
                    ])
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #Only revenue account
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 1)
            self.assertEqual(parameters['accounts'], revenue.code)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, Decimal('600.0'))
            self.assertEqual(debit, Decimal('0.0'))
            self.assertEqual(balance, Decimal('-600.0'))
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #With moves and add initial balance
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 4)
            initial = sum([Decimal(str(m['period_initial_balance']))
                    for m in records])
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, Decimal('350.0'))
            self.assertEqual(debit, Decimal('350.0'))
            results = {
                '41': (Decimal('-80'), Decimal('-130')),
                '43': (Decimal('300'), Decimal('600')),
                '6': (Decimal('80'), Decimal('130')),
                '7': (Decimal('-300'), Decimal('-600')),
                }
            for r in records:
                initial, balance = results[r['code']]
                self.assertEqual(r['period_initial_balance'], initial)
                self.assertEqual(r['period_balance'], balance)
                self.assertEqual(r['initial_balance'], initial)
                self.assertEqual(r['balance'], balance)
            for initial, balance in [(m['period_initial_balance'],
                        m['period_balance']) for m in records]:
                self.assertNotEqual(Decimal(str(initial)), Decimal('0.0'))
                self.assertNotEqual(Decimal(str(balance)), Decimal('0.0'))
                self.assertNotEqual(Decimal(str(balance)),
                    Decimal(str(initial)))
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #With moves, split parties and add initial balance
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 4)
            results = {
                '41': (Decimal('-50'), Decimal('-100')),
                '43': (Decimal('200'), Decimal('500')),
                '6': (Decimal('80'), Decimal('130')),
                '7': (Decimal('-300'), Decimal('-600')),
                }
            for r in records:
                initial, balance = results[r['code']]
                self.assertEqual(r['period_initial_balance'], initial)
                self.assertEqual(r['period_balance'], balance)
                self.assertEqual(r['initial_balance'], initial)
                self.assertEqual(r['balance'], balance)
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #With moves and comparing period
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(parameters['comparison_fiscalyear'],
                fiscalyear.rec_name)
            self.assertEqual(parameters['comparison_start_period'],
                period.rec_name)
            self.assertEqual(parameters['comparison_end_period'],
                period.rec_name)
            self.assertEqual(len(records), 4)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(debit, Decimal('350.0'))
            self.assertEqual(balance, Decimal('0.0'))
            #Comparision data
            credit = sum([Decimal(str(m['credit'])) for m in records])
            debit = sum([Decimal(str(m['debit'])) for m in records])
            balance = sum([Decimal(str(m['balance'])) for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(debit, Decimal('380.0'))
            self.assertEqual(balance, Decimal('0.0'))
            receivable, = self.account.search([
                    ('kind', '=', 'receivable'),
                    ])
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #Splited by parties but move doesn't have any party defined
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 1)
            self.assertEqual(parameters['accounts'], receivable.code)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(debit, Decimal('300.0'))
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(balance, Decimal('300.0'))
            #Inactive customers should always apear on trial balance
            self.party.write([customer1], {
                    'active': False,
                    })
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            #Full splited with parties
            records, parameters = self.trial_balance_report.prepare(data)
            self.assertEqual(len(records), 9)
            self.assertEqual(parameters['split_parties'], True)
            credit = sum([Decimal(str(m['period_credit'])) for m in records])
            debit = sum([Decimal(str(m['period_debit'])) for m in records])
            balance = sum([Decimal(str(m['period_balance'])) for m in records])
            self.assertEqual(credit, Decimal('730.0'))
            self.assertEqual(debit, Decimal('730.0'))

    def test0050taxes_by_invoice(self):
        'Test taxes by invoice'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.create_moves()
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin')])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]
            last_period = fiscalyear.periods[-1]
            account_tax, = self.account.search([
                    ('kind', '=', 'other'),
                    ('company', '=', company.id),
                    ('name', '=', 'Main Tax'),
                    ])
            revenue, = self.account.search([
                    ('kind', '=', 'revenue'),
                    ])
            receivable, = self.account.search([
                    ('kind', '=', 'receivable'),
                    ])
            expense, = self.account.search([
                    ('kind', '=', 'expense'),
                    ])
            payable, = self.account.search([
                    ('kind', '=', 'payable'),
                    ])

            term, = self.payment_term.create([{
                        'name': 'Payment term',
                        'lines': [
                            ('create', [{
                                        'sequence': 0,
                                        'type': 'remainder',
                                        'days': 0,
                                        'months': 0,
                                        'weeks': 0,
                                        }])]
                        }])

            tx = self.taxcode.create([{
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
            tax1, tax2 = self.tax.create([{
                        'name': 'Tax 1',
                        'description': 'Tax 1',
                        'type': 'percentage',
                        'rate': Decimal('.10'),
                        'invoice_account': account_tax.id,
                        'credit_note_account': account_tax.id,
                        'invoice_base_code': invoice_base.id,
                        'invoice_tax_code': invoice_tax.id,
                        'credit_note_base_code': credit_note_base.id,
                        'credit_note_tax_code': credit_note_tax.id,
                        },
                    {
                        'name': 'Tax 2',
                        'description': 'Tax 2',
                        'type': 'percentage',
                        'rate': Decimal('.04'),
                        'invoice_account': account_tax.id,
                        'credit_note_account': account_tax.id,
                        'invoice_base_code': invoice_base.id,
                        'invoice_tax_code': invoice_tax.id,
                        'credit_note_base_code': credit_note_base.id,
                        'credit_note_tax_code': credit_note_tax.id,
                        }])
            customer, = self.party.search([
                    ('name', '=', 'customer1'),
                    ])
            customer_address, = self.party_address.search([
                    ('party', '=', customer.id),
                    ], limit=1)
            supplier, = self.party.search([
                    ('name', '=', 'supplier1'),
                    ])
            supplier_address, = self.party_address.search([
                    ('party', '=', supplier.id),
                    ], limit=1)
            with Transaction().set_context(active_test=False):
                supplier2, = self.party.search([
                        ('name', '=', 'supplier2'),
                        ])
            journal_revenue, = self.journal.search([
                    ('code', '=', 'REV'),
                    ])
            journal_expense, = self.journal.search([
                    ('code', '=', 'EXP'),
                    ])
            invoices = self.invoice.create([{
                        'number': '1',
                        'invoice_date': period.start_date,
                        'company': company.id,
                        'type': 'out_invoice',
                        'currency': company.currency.id,
                        'party': customer.id,
                        'invoice_address': customer_address.id,
                        'journal': journal_revenue.id,
                        'account': receivable.id,
                        'payment_term': term.id,
                        'lines': [
                            ('create', [{
                                        'invoice_type': 'out_invoice',
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
                        'type': 'in_invoice',
                        'currency': company.currency.id,
                        'party': supplier.id,
                        'invoice_address': supplier_address.id,
                        'journal': journal_expense.id,
                        'account': payable.id,
                        'payment_term': term.id,
                        'lines': [
                            ('create', [{
                                        'invoice_type': 'in_invoice',
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
            self.invoice.post(invoices)
            invoice1, invoice2 = invoices
            session_id, _, _ = self.print_taxes_by_invoice.create()
            print_taxes_by_invoice = self.print_taxes_by_invoice(session_id)
            print_taxes_by_invoice.start.company = company
            print_taxes_by_invoice.start.fiscalyear = fiscalyear
            print_taxes_by_invoice.start.periods = []
            print_taxes_by_invoice.start.parties = []
            print_taxes_by_invoice.start.partner_type = 'customers'
            print_taxes_by_invoice.start.grouping = 'invoice'
            print_taxes_by_invoice.start.totals_only = False
            print_taxes_by_invoice.start.output_format = 'pdf'
            _, data = print_taxes_by_invoice.do_print_(None)
            #Customer data
            self.assertEqual(data['company'], company.id)
            self.assertEqual(data['fiscalyear'], fiscalyear.id)
            self.assertEqual(data['partner_type'], 'customers')
            self.assertEqual(data['grouping'], 'invoice')
            self.assertEqual(data['totals_only'], False)
            self.assertEqual(len(data['periods']), 0)
            self.assertEqual(len(data['parties']), 0)
            self.assertEqual(data['output_format'], 'pdf')
            ids, parameters = self.taxes_by_invoice_report.prepare(data)
            records = self.invoice_tax.browse(ids)
            self.assertEqual(len(records), 2)
            self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
            self.assertEqual(parameters['parties'], '')
            self.assertEqual(parameters['periods'], '')
            self.assertEqual(parameters['TOTALS_ONLY'], False)
            base = sum([m.base for m in records])
            tax = sum([m.amount for m in records])
            self.assertEqual(base, Decimal('100.0'))
            self.assertEqual(tax, Decimal('7.0'))
            for tax in records:
                self.assertEqual(tax.invoice, invoice1)
            session_id, _, _ = self.print_taxes_by_invoice.create()
            print_taxes_by_invoice = self.print_taxes_by_invoice(session_id)
            print_taxes_by_invoice.start.company = company
            print_taxes_by_invoice.start.fiscalyear = fiscalyear
            print_taxes_by_invoice.start.periods = []
            print_taxes_by_invoice.start.parties = []
            print_taxes_by_invoice.start.partner_type = 'suppliers'
            print_taxes_by_invoice.start.grouping = 'invoice'
            print_taxes_by_invoice.start.totals_only = False
            print_taxes_by_invoice.start.output_format = 'pdf'
            _, data = print_taxes_by_invoice.do_print_(None)
            #Supplier data
            ids, parameters = self.taxes_by_invoice_report.prepare(data)
            records = self.invoice_tax.browse(ids)
            self.assertEqual(len(records), 2)
            base = sum([m.base for m in records])
            tax = sum([m.amount for m in records])
            self.assertEqual(base, Decimal('40.0'))
            self.assertEqual(tax, Decimal('2.8'))
            for tax in records:
                self.assertEqual(tax.invoice, invoice2)
            session_id, _, _ = self.print_taxes_by_invoice.create()
            print_taxes_by_invoice = self.print_taxes_by_invoice(session_id)
            print_taxes_by_invoice.start.company = company
            print_taxes_by_invoice.start.fiscalyear = fiscalyear
            print_taxes_by_invoice.start.periods = []
            print_taxes_by_invoice.start.parties = [supplier2.id]
            print_taxes_by_invoice.start.partner_type = 'suppliers'
            print_taxes_by_invoice.start.grouping = 'invoice'
            print_taxes_by_invoice.start.totals_only = False
            print_taxes_by_invoice.start.output_format = 'pdf'
            _, data = print_taxes_by_invoice.do_print_(None)
            #Filter by supplier
            ids, parameters = self.taxes_by_invoice_report.prepare(data)
            self.assertEqual(parameters['parties'], supplier2.rec_name)
            records = self.invoice_tax.browse(ids)
            self.assertEqual(len(records), 0)
            session_id, _, _ = self.print_taxes_by_invoice.create()
            print_taxes_by_invoice = self.print_taxes_by_invoice(session_id)
            print_taxes_by_invoice.start.company = company
            print_taxes_by_invoice.start.fiscalyear = fiscalyear
            print_taxes_by_invoice.start.periods = [last_period.id]
            print_taxes_by_invoice.start.parties = []
            print_taxes_by_invoice.start.partner_type = 'suppliers'
            print_taxes_by_invoice.start.grouping = 'invoice'
            print_taxes_by_invoice.start.totals_only = False
            print_taxes_by_invoice.start.output_format = 'pdf'
            _, data = print_taxes_by_invoice.do_print_(None)
            #Filter by periods
            ids, parameters = self.taxes_by_invoice_report.prepare(data)
            self.assertEqual(parameters['periods'], last_period.rec_name)
            records = self.invoice_tax.browse(ids)
            self.assertEqual(len(records), 0)

    def test0060_fiscalyear_not_closed(self):
        'Test fiscalyear not closed'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            today = datetime.date.today()
            fiscalyear, = self.fiscalyear.search([])
            company = fiscalyear.company
            invoice_sequence, = self.sequence_strict.create([{
                        'name': '%s' % today.year,
                        'code': 'account.invoice',
                        'company': company.id,
                        }])
            fiscalyear.out_invoice_sequence = invoice_sequence
            fiscalyear.in_invoice_sequence = invoice_sequence
            fiscalyear.out_credit_note_sequence = invoice_sequence
            fiscalyear.in_credit_note_sequence = invoice_sequence
            fiscalyear.save()
            next_invoice_sequence, = self.sequence_strict.create([{
                        'name': 'Next year invoice',
                        'code': 'account.invoice',
                        'company': company.id,
                        }])
            next_sequence, = self.sequence.create([{
                        'name': 'Next Year',
                        'code': 'account.move',
                        'company': fiscalyear.company.id,
                        }])
            next_fiscalyear, = self.fiscalyear.copy([fiscalyear],
                default={
                    'name': 'Next fiscalyear',
                    'start_date': fiscalyear.start_date + relativedelta(
                        years=1),
                    'end_date': fiscalyear.end_date + relativedelta(years=1),
                    'post_move_sequence': next_sequence.id,
                    'out_invoice_sequence':  next_invoice_sequence,
                    'in_invoice_sequence':  next_invoice_sequence,
                    'out_credit_note_sequence':  next_invoice_sequence,
                    'in_credit_note_sequence':  next_invoice_sequence,
                    'periods': None,
                    })
            self.fiscalyear.create_period([next_fiscalyear])
            self.create_moves(fiscalyear)
            self.create_moves(next_fiscalyear)

            # General ledger for the next year
            period = next_fiscalyear.periods[0]
            last_period = next_fiscalyear.periods[-1]
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.company = company
            print_general_ledger.start.fiscalyear = next_fiscalyear
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = []
            print_general_ledger.start.accounts = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
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
                Decimal('160'),            # Expense
                Decimal('210'),            # Expense
                Decimal('260'),            # Expense
                Decimal('-60'),            # Payable Party 1
                Decimal('-150'),           # Payable Party 2
                Decimal('-200'),           # Payable Party 2
                Decimal('200'),            # Receivable Party 1
                Decimal('700'),            # Receivable Party 2
                Decimal('1000'),           # Receivable Party 2
                Decimal('-700'),           # Revenue
                Decimal('-900'),           # Revenue
                Decimal('-1200'),          # Revenue
                ]
            for record, balance in zip(records, balances):
                self.assertEqual(record['balance'], balance)

            # Trial for the next year
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            records, parameters = self.trial_balance_report.prepare(data)
            balances = {
                'Main Cash': Decimal('0'),
                'Main Tax': Decimal('0'),
                'View': Decimal('0'),
                'supplier1': Decimal('-30'),
                'supplier2': Decimal('-100'),
                'customer1': Decimal('100'),
                'customer2': Decimal('500'),
                'Main Expense': Decimal('130'),
                'Main Revenue': Decimal('-600'),
                }
            for record in records:
                self.assertEqual(record['period_initial_balance'],
                    balances[record['name']])
                self.assertEqual(record['initial_balance'],
                    balances[record['name']])

            # Create another fiscalyear and test it cumulates correctly
            future_invoice_sequence, = self.sequence_strict.create([{
                        'name': 'Future year invoice',
                        'code': 'account.invoice',
                        'company': company.id,
                        }])
            future_sequence, = self.sequence.create([{
                        'name': 'Future Year',
                        'code': 'account.move',
                        'company': fiscalyear.company.id,
                        }])
            future_fiscalyear, = self.fiscalyear.copy([fiscalyear],
                default={
                    'name': 'Future fiscalyear',
                    'start_date': fiscalyear.start_date + relativedelta(
                        years=2),
                    'end_date': fiscalyear.end_date + relativedelta(years=2),
                    'post_move_sequence': future_sequence.id,
                    'out_invoice_sequence':  future_invoice_sequence,
                    'in_invoice_sequence':  future_invoice_sequence,
                    'out_credit_note_sequence':  future_invoice_sequence,
                    'in_credit_note_sequence':  future_invoice_sequence,
                    'periods': None,
                    })
            self.fiscalyear.create_period([future_fiscalyear])
            self.create_moves(future_fiscalyear)

            period = future_fiscalyear.periods[0]
            last_period = future_fiscalyear.periods[-1]
            session_id, _, _ = self.print_trial_balance.create()
            print_trial_balance = self.print_trial_balance(session_id)
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
            records, parameters = self.trial_balance_report.prepare(data)
            balances = {
                'Main Cash': Decimal('0'),
                'Main Tax': Decimal('0'),
                'View': Decimal('0'),
                'supplier1': Decimal('-60'),
                'supplier2': Decimal('-200'),
                'customer1': Decimal('200'),
                'customer2': Decimal('1000'),
                'Main Expense': Decimal('260'),
                'Main Revenue': Decimal('-1200'),
                }
            for record in records:
                self.assertEqual(record['period_initial_balance'],
                    balances[record['name']])
                self.assertEqual(record['initial_balance'],
                    balances[record['name']])


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        # Skip doctest
        class_name = test.__class__.__name__
        if test not in suite and class_name != 'DocFileCase':
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountJasperReportsTestCase))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

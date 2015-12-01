# This file is part of the account_jasper_reports module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class AccountJasperReportsTestCase(ModuleTestCase):
    'Test Account Jasper Reports module'
    module = 'account_jasper_reports'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountJasperReportsTestCase))
    return suite
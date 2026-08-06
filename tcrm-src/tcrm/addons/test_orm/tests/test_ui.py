import tcrm.tests
from tcrm.tools import mute_logger

from tcrm.addons.base.tests.common import HttpCaseWithUserDemo


@tcrm.tests.common.tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo):

    def test_01_admin_widget_x2many(self):
        # FIXME: breaks if too many children of base.menu_tests

        # This tour turns out to be quite sensible to the number of items in
        # the base.menu_tests: it's specifically sequenced to be lower (after)
        # the default, but doesn't account for the fact that it could
        # "fall off" into the "o_extra_menu_items" section if the window is
        # too small or there are too many items preceding it in the tests menu
        self.start_tour("/tcrm/action-test_orm.action_discussions",
            'widget_x2many', login="admin", timeout=120)


@tcrm.tests.tagged('-at_install', 'post_install')
class TestUiTranslation(tcrm.tests.HttpCase):

    @mute_logger('tcrm.sql_db', 'tcrm.http')
    def test_01_sql_constraints(self):
        # Raise an SQL constraint and test the message
        self.env['res.lang']._activate_lang('fr_FR')
        self.env.ref('base.module_test_orm')._update_translations(['fr_FR'])
        constraint = self.env.ref('test_orm.constraint_test_orm_category_positive_color')
        message = constraint.with_context(lang='fr_FR').message
        self.assertEqual(message, "La couleur doit être une valeur positive !")

        # TODO: make the test work with French translations. As the transaction
        # is rollbacked at insert and a new cursor is opened, can not test that
        # the message is translated (_load_module_terms is also) rollbacked.
        # Test individually the external id and loading of translation.
        self.start_tour("/tcrm/action-test_orm.action_categories",
            'sql_constaint', login="admin")

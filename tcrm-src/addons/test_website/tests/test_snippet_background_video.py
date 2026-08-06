# Part of Tcrm. See LICENSE file for full copyright and licensing details.

import tcrm.tests


@tcrm.tests.common.tagged('post_install', '-at_install')
class TestSnippetBackgroundVideo(tcrm.tests.HttpCase):

    def test_snippet_background_video(self):
        self.start_tour("/", "snippet_background_video", login="admin")

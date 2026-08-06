import { expect, test } from "@tcrm/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Component, useState, xml } from "@tcrm/owl";
import { tcrmLogo } from "@point_of_sale/app/components/tcrm_logo/tcrm_logo";
import { CenteredIcon } from "@point_of_sale/app/components/centered_icon/centered_icon";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import { registry } from "@web/core/registry";
import { waitFor } from "@tcrm/hoot-dom";

test("test that generic components can be mounted; the goal is to ensure that they don't have any unmet dependencies", async () => {
    class TestComponent extends Component {
        static props = [];
        static components = {
            tcrmLogo,
            CenteredIcon,
            Input,
            NumericInput,
        };
        static template = xml`
            <div class="test-container">
                <tcrmLogo />
                <CenteredIcon icon="'fa-smile'"/>
                <Input tModel="[state, 'number']"/>
                <NumericInput tModel="[state, 'number']" />
            </div>
        `;
        setup() {
            this.state = useState({ number: 1 });
        }
    }

    registry.category("services").content = {};

    await mountWithCleanup(TestComponent, {
        noMainContainer: true,
    });
    await waitFor("div.test-container");
    expect(true).toBe(true);
});

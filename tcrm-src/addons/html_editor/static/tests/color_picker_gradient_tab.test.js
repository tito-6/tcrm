import { test, expect } from "@tcrm/hoot";
import { animationFrame, click } from "@tcrm/hoot-dom";
import { ColorPicker } from "@web/core/color_picker/color_picker";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

test("custom gradient must be defined", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "gradient",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
            enabledTabs: ["gradient"],
        },
    });
    await click(".o_custom_gradient_button");
    await animationFrame();
    expect(".gradient-colors input[type='range']").toHaveCount(2);
});

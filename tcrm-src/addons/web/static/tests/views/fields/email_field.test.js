import { expect, getFixture, test } from "@tcrm/hoot";
import {
    contains,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
} from "../../web_test_helpers";
import { queryAllTexts, queryFirst } from "@tcrm/hoot-dom";

class Contact extends models.Model {
    email = fields.Char();
}

defineModels([Contact]);

onRpc("has_group", () => true);

test("in form view", async () => {
    Contact._records = [{ id: 1, email: "john.doe@tcrm.com" }];
    await mountView({
        type: "form",
        resModel: "contact",
        resId: 1,
        arch: `<form><field name="email" widget="email"/></form>`,
    });
    expect(`.o_field_email input[type="email"]`).toHaveCount(1);
    expect(`.o_field_email input[type="email"]`).toHaveValue("john.doe@tcrm.com");
    expect(`.o_field_email a`).toHaveCount(1);
    expect(`.o_field_email a`).toHaveAttribute("href", "mailto:john.doe@tcrm.com");
    expect(`.o_field_email a`).toHaveAttribute("target", "_blank");
    await fieldInput("email").edit("new@tcrm.com");
    expect(`.o_field_email input[type="email"]`).toHaveValue("new@tcrm.com");
});

test("in editable list view", async () => {
    Contact._records = [
        { id: 1, email: "john.doe@tcrm.com" },
        { id: 2, email: "jane.doe@tcrm.com" },
    ];
    await mountView({
        type: "list",
        resModel: "contact",
        arch: '<list editable="bottom"><field name="email" widget="email"/></list>',
    });
    expect(`tbody td:not(.o_list_record_selector) a`).toHaveCount(2);
    expect(`.o_field_email a`).toHaveCount(2);
    expect(queryAllTexts(`tbody td:not(.o_list_record_selector) a`)).toEqual([
        "john.doe@tcrm.com",
        "jane.doe@tcrm.com",
    ]);
    expect(".o_field_email a:first").toHaveAttribute("href", "mailto:john.doe@tcrm.com");
    let cell = queryFirst("tbody td:not(.o_list_record_selector)");
    await contains(cell).click();
    expect(cell.parentElement).toHaveClass("o_selected_row");
    expect(`.o_field_email input[type="email"]`).toHaveValue("john.doe@tcrm.com");
    await fieldInput("email").edit("new@tcrm.com");
    await contains(getFixture()).click();
    cell = queryFirst("tbody td:not(.o_list_record_selector)");
    expect(cell.parentElement).not.toHaveClass("o_selected_row");
    expect(queryAllTexts(`tbody td:not(.o_list_record_selector) a`)).toEqual([
        "new@tcrm.com",
        "jane.doe@tcrm.com",
    ]);
    expect(".o_field_email a:first").toHaveAttribute("href", "mailto:new@tcrm.com");
});

test("with empty value", async () => {
    await mountView({
        type: "form",
        resModel: "contact",
        arch: `<form><field name="email" widget="email" placeholder="Placeholder"/></form>`,
    });
    expect(`.o_field_email input`).toHaveValue("");
});

test("with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "contact",
        arch: `<form><field name="email" widget="email" placeholder="Placeholder"/></form>`,
    });
    expect(`.o_field_email input`).toHaveAttribute("placeholder", "Placeholder");
});

test("placeholder_field shows as placeholder", async () => {
    Contact._fields.char = fields.Char({
        default: "My Placeholder",
    });
    await mountView({
        type: "form",
        resModel: "contact",
        arch: `<form>
            <field name="email" widget="email" options="{'placeholder_field' : 'char'}"/>
            <field name="char"/>
        </form>`,
    });
    expect(`.o_field_email input`).toHaveAttribute("placeholder", "My Placeholder");
});

test("trim user value", async () => {
    await mountView({
        type: "form",
        resModel: "contact",
        arch: '<form><field name="email" widget="email"/></form>',
    });

    await fieldInput("email").edit("   hello@gmail.com    ");
    await contains(getFixture()).click();
    expect(`.o_field_email input`).toHaveValue("hello@gmail.com");
});

test("onchange scenario with readonly", async () => {
    Contact._fields.phone = fields.Char({
        onChange: (record) => {
            record.email = "onchange@domain.ext";
        },
    });
    Contact._records = [{ id: 1, email: "default@domain.ext" }];
    await mountView({
        type: "form",
        resModel: "contact",
        resId: 1,
        arch: `<form><field name="phone"/><field name="email" widget="email" readonly="1"/></form>`,
    });
    expect(`.o_field_email`).toHaveText("default@domain.ext");
    await fieldInput("phone").edit("047412345");
    expect(`.o_field_email`).toHaveText("onchange@domain.ext");
});

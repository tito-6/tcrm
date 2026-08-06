import { beforeEach, describe, expect, test } from "@tcrm/hoot";
import { getService, makeMockEnv } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

let titleService;

beforeEach(async () => {
    await makeMockEnv();
    titleService = getService("title");
});

test("simple title", () => {
    titleService.setParts({ one: "Mytcrm" });
    expect(titleService.current).toBe("Mytcrm");
});

test("add title part", () => {
    titleService.setParts({ one: "Mytcrm", two: null });
    expect(titleService.current).toBe("Mytcrm");
    titleService.setParts({ three: "Import" });
    expect(titleService.current).toBe("Mytcrm - Import");
});

test("modify title part", () => {
    titleService.setParts({ one: "Mytcrm" });
    expect(titleService.current).toBe("Mytcrm");
    titleService.setParts({ one: "Zopenerp" });
    expect(titleService.current).toBe("Zopenerp");
});

test("delete title part", () => {
    titleService.setParts({ one: "Mytcrm" });
    expect(titleService.current).toBe("Mytcrm");
    titleService.setParts({ one: null });
    expect(titleService.current).toBe("Tcrm");
});

test("all at once", () => {
    titleService.setParts({ one: "Mytcrm", two: "Import" });
    expect(titleService.current).toBe("Mytcrm - Import");
    titleService.setParts({ one: "Zopenerp", two: null, three: "Sauron" });
    expect(titleService.current).toBe("Zopenerp - Sauron");
});

test("get title parts", () => {
    expect(titleService.current).toBe("");
    titleService.setParts({ one: "Mytcrm", two: "Import" });
    expect(titleService.current).toBe("Mytcrm - Import");
    const parts = titleService.getParts();
    expect(parts).toEqual({ one: "Mytcrm", two: "Import" });
    parts.action = "Export";
    expect(titleService.current).toBe("Mytcrm - Import"); // parts is a copy!
});

import { describe, expect, it } from "vitest";
import { listAnd } from "../../src/main/application/spanishList";

describe("listAnd", () => {
  it("shouldUseEBeforeAnIWhenTheLastNameStartsWithTheISound", () => {
    expect(listAnd(["Siemens", "IBM"])).toBe("Siemens e IBM");
    expect(listAnd(["Siemens", "Hilti"])).toBe("Siemens e Hilti");
  });
  it("shouldKeepYWhenTheNameStartsWithHiOrIBeforeAVowel", () => {
    expect(listAnd(["Siemens", "Hierros"])).toBe("Siemens y Hierros");
    expect(listAnd(["Siemens", "Ion Tech"])).toBe("Siemens y Ion Tech");
  });
  it("shouldJoinThreeNamesWithCommasAndHandleOneOrNone", () => {
    expect(listAnd(["A", "B", "C"])).toBe("A, B y C");
    expect(listAnd(["A"])).toBe("A");
    expect(listAnd([])).toBe("");
  });
});

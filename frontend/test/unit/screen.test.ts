import { describe, expect, it } from "vitest";
import { chooseScreen } from "../../src/main/application/screen";

describe("chooseScreen", () => {
  it("shouldChooseTheTopicsScreenForTheTemasPath", () => {
    expect(chooseScreen("/temas", "")).toBe("topics");
    expect(chooseScreen("/temas/", "")).toBe("topics");
  });
  it("shouldKeepTheOtherScreensWhenThePathIsNotTemas", () => {
    expect(chooseScreen("/", "")).toBe("whitespace");
    expect(chooseScreen("/matches", "")).toBe("matcher");
  });
});

import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

test.skip(!existsSync(fileURLToPath(new URL("../../../data/snapshots/operational_corpus_v1", import.meta.url))), "frozen artifacts are not in this checkout");

test("shouldShowFiveAssetsAndFollowTheirSourceWhenADemoDemandIsChosen", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /new available technologies for water quality measurement/ }).click();

  await expect(page.getByRole("link", { name: "Ver demanda original" })).toBeVisible();
  const results = page.getByRole("region", { name: "Resultados" });
  await expect(results.getByRole("article")).toHaveCount(5);
  await expect(results.getByText(/Mostrando 5 de [\d.]+ activos elegibles/)).toBeVisible();

  const first = results.getByRole("article").first();
  await expect(first.getByRole("heading", { name: "Fuente de agua potable" })).toBeVisible();
  await expect(first.getByText(/Fuente de agua potable \(10\) caracterizada/)).toBeVisible();

  const source = first.getByRole("link", { name: "Google Patents" });
  await expect(source).toHaveAttribute("href", "https://patents.google.com/patent/ES1295722U");
  await expect(source).toHaveAttribute("target", "_blank");
});

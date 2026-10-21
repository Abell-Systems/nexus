import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

test.skip(!existsSync(fileURLToPath(new URL("../../../data/snapshots/operational_corpus_v1", import.meta.url))), "frozen artifacts are not in this checkout");

test("shouldDescribeTheCorpusWithoutPresentingAbsencesAsOpportunitiesOnTheFrontPage", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Cobertura y ausencias del corpus de patentes" })).toBeVisible();
  await expect(page.getByText("Origen de los datos: Oficina Española de Patentes y Marcas")).toBeVisible();
  await expect(page.getByText("White spaces predictivos: no disponible. Pendiente de validación científica.")).toBeVisible();
  await expect(page.getByRole("table", { name: /% de pares de subclases activas ya vistos juntos/ })).toHaveCount(2);
  await expect(page.getByText(/oportunidades? (tecnol[oó]gica|de innovaci[oó]n) (detectad|identificad|encontrad)/i)).toHaveCount(0);
});

test("shouldKeepAnchorsWorkingAndFitThePhoneWidthWhenTheFrontPageIsOpenedOnAPhone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("link", { name: "Trazabilidad" }).click();
  await expect(page).toHaveURL(/#trazabilidad$/);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("shouldKeepTheMatcherReachableOnItsOwnAddressAndOnSharedLinks", async ({ page }) => {
  await page.goto("/matches");
  await expect(page.getByRole("heading", { name: "De una demanda real a activos españoles" })).toBeVisible();
  await page.goto("/?demanda=does-not-exist");
  await expect(page.getByRole("heading", { name: "De una demanda real a activos españoles" })).toBeVisible();
});

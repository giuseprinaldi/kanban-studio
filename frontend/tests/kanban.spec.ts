import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  
  // If the Login screen is shown, fill credentials and sign in
  const loginHeading = page.getByRole("heading", { name: "Sign In" });
  if (await loginHeading.isVisible()) {
    await page.locator("#username").fill("user");
    await page.locator("#password").fill("password");
    await page.getByRole("button", { name: "Sign In" }).click();
  }
  
  // Wait for the Kanban board to load
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  // Reset the board to initialData so that every test run starts with a clean database board state
  await page.evaluate(async () => {
    const initialData = {
      columns: [
        { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
        { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
        { id: "col-progress", title: "In Progress", cardIds: ["card-4", "card-5"] },
        { id: "col-review", title: "Review", cardIds: ["card-6"] },
        { id: "col-done", title: "Done", cardIds: ["card-7", "card-8"] },
      ],
      cards: {
        "card-1": {
          id: "card-1",
          title: "Align roadmap themes",
          details: "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
          id: "card-2",
          title: "Gather customer signals",
          details: "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
          id: "card-3",
          title: "Prototype analytics view",
          details: "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
          id: "card-4",
          title: "Refine status language",
          details: "Standardize column labels and tone across the board.",
        },
        "card-5": {
          id: "card-5",
          title: "Design card layout",
          details: "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
          id: "card-6",
          title: "QA micro-interactions",
          details: "Verify hover, focus, and loading states.",
        },
        "card-7": {
          id: "card-7",
          title: "Ship marketing page",
          details: "Final copy approved and asset pack delivered.",
        },
        "card-8": {
          id: "card-8",
          title: "Close onboarding sprint",
          details: "Document release notes and share internally.",
        },
      },
    };

    await fetch("/api/kanban", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(initialData),
    });
  });

  // Reload the page to reflect the reset board layout
  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
});

test("loads the kanban board", async ({ page }) => {
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  
  const cardTitle = `Playwright card ${Date.now()}`;
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(cardTitle)).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  // Hover over card center (Playwright automatically scrolls and centers the pointer)
  await card.hover();
  await page.mouse.down();
  
  // Move 10 pixels down to trigger activation constraint (distance: 6)
  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2 + 10,
    { steps: 3 }
  );
  await page.waitForTimeout(200);

  // Move to target column
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 150,
    { steps: 15 }
  );
  await page.mouse.up();
  
  // Verify card successfully moved to Review column
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});






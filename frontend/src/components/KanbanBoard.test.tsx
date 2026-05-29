import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";
import { vi } from "vitest";

// Mock global fetch
global.fetch = vi.fn().mockImplementation((url) => {
  if (url === "/api/kanban") {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(JSON.parse(JSON.stringify(initialData))),
    });
  }
  if (url === "/api/auth/logout") {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: "success" }),
    });
  }
  return Promise.reject(new Error(`Unhandled request to ${url}`));
});

const getFirstColumn = async () => {
  const columns = await screen.findAllByTestId(/column-/i);
  return columns[0];
};

describe("KanbanBoard", () => {
  it("renders five columns", async () => {
    render(<KanbanBoard />);
    const columns = await screen.findAllByTestId(/column-/i);
    expect(columns).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(await within(column).findByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});

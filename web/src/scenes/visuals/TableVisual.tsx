import type { TableVisual as TableData } from "../../types";

/**
 * A real data table: column headers, and the first cell of each row as the
 * row's header, so a screen reader can say "Year 2, Charge on the amount
 * repaid, 1%" as you move through it.
 */
export function TableVisual({ visual }: { visual: TableData }) {
  return (
    <div className="visual visual--table">
      <table className="data-table">
        <thead>
          <tr>
            {visual.columns.map((column) => (
              <th key={column} scope="col">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visual.rows.map(([rowHeader, ...cells]) => (
            <tr key={rowHeader}>
              <th scope="row">{rowHeader}</th>
              {cells.map((cell, index) => (
                <td key={index}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {visual.footnote && <p className="data-table__footnote">{visual.footnote}</p>}
    </div>
  );
}
